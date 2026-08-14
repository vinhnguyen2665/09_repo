from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import authenticate_user_from_request
from app.models.repository import Repository, RepoFormat
from app.models.user import UserRole
from app.services.pypi_engine import pypi_engine

router = APIRouter(tags=["Python PyPI Registry"])

async def get_pypi_repo(repo_name: str, db: AsyncSession) -> Repository:
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
    if repo.format != RepoFormat.PYPI:
        raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' is not a PyPI repository")
    return repo

# 1. Simple Index Root (PEP 503)
@router.get("/repository/{repo_name}/simple/")
@router.get("/repository/{repo_name}/simple")
async def get_simple_index(repo_name: str, db: AsyncSession = Depends(get_db)):
    repo = await get_pypi_repo(repo_name, db)
    return await pypi_engine.get_simple_index(db, repo)

# 2. Package Page (PEP 503)
@router.get("/repository/{repo_name}/simple/{package_name}/")
@router.get("/repository/{repo_name}/simple/{package_name}")
async def get_package_page(
    repo_name: str,
    package_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_pypi_repo(repo_name, db)
    base_url = str(request.base_url)
    return await pypi_engine.get_package_page(db, repo, package_name, base_url=base_url)

# 3. Package File Download
@router.get("/repository/{repo_name}/packages/{filename}")
async def get_package_file(
    repo_name: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = await get_pypi_repo(repo_name, db)
    range_header = request.headers.get("Range")
    return await pypi_engine.get_package_file(db, repo, filename, range_header=range_header)

# 4. Twine Upload Endpoint (POST)
@router.post("/repository/{repo_name}/")
@router.post("/repository/{repo_name}")
@router.post("/repository/{repo_name}/upload")
async def upload_pypi_package(
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to upload packages")

    repo = await get_pypi_repo(repo_name, db)
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
