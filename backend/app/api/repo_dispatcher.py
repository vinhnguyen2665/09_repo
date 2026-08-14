import json
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, generate_api_token
from app.core.rbac import authenticate_user_from_request
from app.models.repository import Repository, RepoFormat, RepoType
from app.models.user import User, UserRole, ApiToken
from app.services.maven_engine import maven_engine
from app.services.npm_engine import npm_engine
from app.services.pypi_engine import pypi_engine
from app.services.storage import storage_service

router = APIRouter(tags=["Package Repositories Gateway"])

async def get_repo(repo_name: str, db: AsyncSession) -> Repository:
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
    if not repo.is_online:
        raise HTTPException(status_code=503, detail=f"Repository '{repo_name}' is currently offline")
    return repo

# ----------------- GET & HEAD Handlers -----------------

@router.get("/repository/{repo_name}/{path:path}")
async def repository_get_gateway(
    repo_name: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_repo(repo_name, db)
    range_header = request.headers.get("Range")
    base_url = str(request.base_url)
    clean_path = path.strip("/")

    # MAVEN
    if repo.format == RepoFormat.MAVEN:
        return await maven_engine.get_artifact(db, repo, clean_path, range_header=range_header)

    # NPM
    elif repo.format == RepoFormat.NPM:
        # Check if tarball download: {package}/-/{tarball}
        if "/-/" in clean_path:
            pkg_name, tarball_fn = clean_path.split("/-/", 1)
            return await npm_engine.get_tarball(db, repo, pkg_name, tarball_fn, range_header=range_header)
        # Package metadata JSON
        return await npm_engine.get_package_metadata(db, repo, clean_path, base_url=base_url)

    # PYPI
    elif repo.format == RepoFormat.PYPI:
        if clean_path == "simple" or clean_path == "":
            return await pypi_engine.get_simple_index(db, repo)
        elif clean_path.startswith("simple/"):
            pkg_name = clean_path[7:].strip("/")
            return await pypi_engine.get_package_page(db, repo, pkg_name, base_url=base_url)
        elif clean_path.startswith("packages/"):
            fn = clean_path[9:].strip("/")
            return await pypi_engine.get_package_file(db, repo, fn, range_header=range_header)
        else:
            # Fallback to package page or simple index
            return await pypi_engine.get_package_page(db, repo, clean_path, base_url=base_url)

    raise HTTPException(status_code=400, detail=f"Unsupported repository format '{repo.format}'")

@router.get("/repository/{repo_name}")
async def repository_root_get(
    repo_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await repository_get_gateway(repo_name, "", request, db)

@router.head("/repository/{repo_name}/{path:path}")
async def repository_head_gateway(
    repo_name: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_repo(repo_name, db)
    clean_path = path.strip("/")
    if await storage_service.file_exists(repo.name, clean_path):
        info = await storage_service.get_file_info(repo.name, clean_path)
        return Response(
            status_code=200,
            headers={
                "Content-Length": str(info["size_bytes"]),
                "Content-Type": info["content_type"],
                "Accept-Ranges": "bytes"
            }
        )
    raise HTTPException(status_code=404, detail="Artifact not found")

# ----------------- PUT Handlers (Upload / Publish) -----------------

@router.put("/repository/{repo_name}/{path:path}", status_code=status.HTTP_201_CREATED)
async def repository_put_gateway(
    repo_name: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    clean_path = path.strip("/")

    # Check for NPM couchdb user login/create: /repository/{repo_name}/-/user/org.couchdb.user:{username}
    if "/-/user/org.couchdb.user:" in clean_path:
        username = clean_path.split("/-/user/org.couchdb.user:")[-1]
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        password = body.get("password")
        stmt = select(User).where(User.username == username)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            return JSONResponse(status_code=401, content={"error": "Unauthorized", "reason": "Bad credentials"})

        raw_token, prefix, token_hash = generate_api_token(user.id)
        token_obj = ApiToken(
            user_id=user.id,
            name=f"npm-cli-{prefix}",
            token_hash=token_hash,
            token_prefix=prefix
        )
        db.add(token_obj)
        await db.commit()

        return JSONResponse(
            status_code=201,
            content={"ok": True, "id": f"org.couchdb.user:{username}", "token": raw_token}
        )

    # All other PUT operations require authentication
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for package publishing",
            headers={"WWW-Authenticate": 'Basic realm="Zero9Repo"'}
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to publish")

    repo = await get_repo(repo_name, db)

    # MAVEN PUT
    if repo.format == RepoFormat.MAVEN:
        async def body_stream():
            async for chunk in request.stream():
                yield chunk
        return await maven_engine.put_artifact(db, repo, clean_path, body_stream())

    # NPM PUT (publish)
    elif repo.format == RepoFormat.NPM:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON publish payload")
        return await npm_engine.publish_package(db, repo, body)

    raise HTTPException(status_code=400, detail=f"PUT not supported on format '{repo.format}'")

# ----------------- POST Handlers (PyPI / Twine upload) -----------------

@router.post("/repository/{repo_name}/")
@router.post("/repository/{repo_name}")
@router.post("/repository/{repo_name}/upload")
async def repository_post_gateway(
    repo_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for twine upload",
            headers={"WWW-Authenticate": 'Basic realm="Zero9Repo"'}
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to upload")

    repo = await get_repo(repo_name, db)
    if repo.format == RepoFormat.PYPI:
        form = await request.form()
        content_file = form.get("content")
        if not content_file or not hasattr(content_file, "filename"):
            raise HTTPException(status_code=400, detail="Missing file content upload")

        name = form.get("name", "unknown")
        version = form.get("version", "0.0.0")

        return await pypi_engine.upload_package(
            db=db,
            repo=repo,
            file=content_file,
            name=str(name),
            version=str(version)
        )

    raise HTTPException(status_code=400, detail=f"POST upload not supported on format '{repo.format}'")
