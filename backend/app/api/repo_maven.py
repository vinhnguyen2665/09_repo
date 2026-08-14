from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_optional_current_user, authenticate_user_from_request
from app.models.repository import Repository, RepoFormat, RepoType
from app.models.user import UserRole
from app.services.maven_engine import maven_engine
from app.services.storage import storage_service

router = APIRouter(tags=["Maven / Gradle Registry"])

async def get_maven_repo(repo_name: str, db: AsyncSession) -> Repository:
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
    if repo.format != RepoFormat.MAVEN:
        raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' is not a Maven repository")
    return repo

@router.get("/repository/{repo_name}/{artifact_path:path}")
async def get_maven_artifact(
    repo_name: str,
    artifact_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_maven_repo(repo_name, db)
    range_header = request.headers.get("Range")
    return await maven_engine.get_artifact(db, repo, artifact_path, range_header=range_header)

@router.head("/repository/{repo_name}/{artifact_path:path}")
async def head_maven_artifact(
    repo_name: str,
    artifact_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_maven_repo(repo_name, db)
    # Check existence
    if await storage_service.file_exists(repo.name, artifact_path):
        info = await storage_service.get_file_info(repo.name, artifact_path)
        return Response(
            status_code=200,
            headers={
                "Content-Length": str(info["size_bytes"]),
                "Content-Type": info["content_type"],
                "Accept-Ranges": "bytes"
            }
        )
    raise HTTPException(status_code=404, detail="Artifact not found")

@router.put("/repository/{repo_name}/{artifact_path:path}", status_code=status.HTTP_201_CREATED)
async def put_maven_artifact(
    repo_name: str,
    artifact_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Require Authentication for uploads
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for artifact deployment",
            headers={"WWW-Authenticate": "Basic realm=\"Zero9Repo\""}
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to upload")

    repo = await get_maven_repo(repo_name, db)

    async def body_stream():
        async for chunk in request.stream():
            yield chunk

    result = await maven_engine.put_artifact(db, repo, artifact_path, body_stream())
    return result
