import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, generate_api_token
from app.core.rbac import authenticate_user_from_request
from app.models.repository import Repository, RepoFormat
from app.models.user import User, UserRole, ApiToken
from app.services.npm_engine import npm_engine

router = APIRouter(tags=["NPM Registry"])

async def get_npm_repo(repo_name: str, db: AsyncSession) -> Repository:
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
    if repo.format != RepoFormat.NPM:
        raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' is not an NPM repository")
    return repo

# 1. NPM CouchDB User Login / Registration
@router.put("/repository/{repo_name}/-/user/org.couchdb.user:{username}")
@router.put("/-/user/org.couchdb.user:{username}")
async def npm_user_auth(
    username: str,
    request: Request,
    repo_name: Optional[str] = "npm-private",
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    password = body.get("password")
    
    # Authenticate existing user
    stmt = select(User).where(User.username == username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        if not verify_password(password, user.hashed_password):
            return JSONResponse(status_code=401, content={"error": "Unauthorized", "reason": "Bad credentials"})
    else:
        # If user does not exist, reject or create reader
        return JSONResponse(status_code=401, content={"error": "Unauthorized", "reason": "User not found"})

    # Create token for NPM CLI
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
        content={
            "ok": True,
            "id": f"org.couchdb.user:{username}",
            "token": raw_token
        }
    )

# 2. Package Tarball Download
@router.get("/repository/{repo_name}/{package_name:path}/-/{tarball_filename}")
async def get_npm_tarball(
    repo_name: str,
    package_name: str,
    tarball_filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_npm_repo(repo_name, db)
    range_header = request.headers.get("Range")
    return await npm_engine.get_tarball(db, repo, package_name, tarball_filename, range_header=range_header)

# 3. Package Metadata GET
@router.get("/repository/{repo_name}/{package_name:path}")
async def get_npm_metadata(
    repo_name: str,
    package_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_npm_repo(repo_name, db)
    base_url = str(request.base_url)
    return await npm_engine.get_package_metadata(db, repo, package_name, base_url=base_url)

# 4. Package Publish PUT
@router.put("/repository/{repo_name}/{package_name:path}", status_code=status.HTTP_201_CREATED)
async def publish_npm_package(
    repo_name: str,
    package_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for npm publish"
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to publish")

    repo = await get_npm_repo(repo_name, db)
    
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid publish payload")

    return await npm_engine.publish_package(db, repo, body)
