from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_admin, require_reader, get_current_user
from app.models.repository import Repository, RepoFormat, RepoType
from app.models.artifact import Artifact
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryUpdate, RepositoryOut
from app.core.config import settings

router = APIRouter(prefix="/repositories", tags=["Repositories Management"])

def _format_endpoint_url(repo: Repository, request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    if repo.format == RepoFormat.DOCKER:
        return f"{base}/v2"
    elif repo.format == RepoFormat.PYPI:
        return f"{base}/repository/{repo.name}/simple"
    else:
        return f"{base}/repository/{repo.name}"

@router.get("", response_model=List[RepositoryOut])
async def list_repositories(
    request: Request,
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Repository).order_by(Repository.format.asc(), Repository.name.asc())
    res = await db.execute(stmt)
    repos = res.scalars().all()

    # Query counts & sizes
    stats_stmt = select(
        Artifact.repo_name,
        func.count(Artifact.id).label("count"),
        func.sum(Artifact.size_bytes).label("total_size")
    ).group_by(Artifact.repo_name)
    stats_res = await db.execute(stats_stmt)
    stats_map = {row[0]: (row[1] or 0, row[2] or 0) for row in stats_res.all()}

    output = []
    for r in repos:
        count, size = stats_map.get(r.name, (0, 0))
        out = RepositoryOut.model_validate(r)
        out.endpoint_url = _format_endpoint_url(r, request)
        out.total_artifacts = count
        out.total_size_bytes = size
        output.append(out)

    return output

@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def create_repository(
    req: RepositoryCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Repository).where(Repository.name == req.name)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Repository '{req.name}' already exists")

    new_repo = Repository(
        name=req.name,
        format=req.format,
        type=req.type,
        description=req.description or "",
        is_online=req.is_online,
        upstream_url=req.upstream_url,
        cache_ttl_hours=req.cache_ttl_hours or 720,
        member_repo_names=req.member_repo_names or [],
        extra_config=req.extra_config or {}
    )
    db.add(new_repo)
    await db.commit()
    await db.refresh(new_repo)

    out = RepositoryOut.model_validate(new_repo)
    out.endpoint_url = _format_endpoint_url(new_repo, request)
    return out

@router.get("/{repo_id_or_name}", response_model=RepositoryOut)
async def get_repository(
    repo_id_or_name: str,
    request: Request,
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    if repo_id_or_name.isdigit():
        stmt = select(Repository).where(Repository.id == int(repo_id_or_name))
    else:
        stmt = select(Repository).where(Repository.name == repo_id_or_name)
    
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get stats
    stats_stmt = select(
        func.count(Artifact.id),
        func.sum(Artifact.size_bytes)
    ).where(Artifact.repo_name == repo.name)
    stats_res = await db.execute(stats_stmt)
    count, size = stats_res.first() or (0, 0)

    out = RepositoryOut.model_validate(repo)
    out.endpoint_url = _format_endpoint_url(repo, request)
    out.total_artifacts = count or 0
    out.total_size_bytes = size or 0
    return out

@router.put("/{repo_id_or_name}", response_model=RepositoryOut)
async def update_repository(
    repo_id_or_name: str,
    req: RepositoryUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if repo_id_or_name.isdigit():
        stmt = select(Repository).where(Repository.id == int(repo_id_or_name))
    else:
        stmt = select(Repository).where(Repository.name == repo_id_or_name)

    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if req.description is not None:
        repo.description = req.description
    if req.is_online is not None:
        repo.is_online = req.is_online
    if req.upstream_url is not None:
        repo.upstream_url = req.upstream_url
    if req.cache_ttl_hours is not None:
        repo.cache_ttl_hours = req.cache_ttl_hours
    if req.member_repo_names is not None:
        repo.member_repo_names = req.member_repo_names
    if req.extra_config is not None:
        repo.extra_config = req.extra_config

    await db.commit()
    await db.refresh(repo)

    out = RepositoryOut.model_validate(repo)
    out.endpoint_url = _format_endpoint_url(repo, request)
    return out

@router.delete("/{repo_id_or_name}")
async def delete_repository(
    repo_id_or_name: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if repo_id_or_name.isdigit():
        stmt = select(Repository).where(Repository.id == int(repo_id_or_name))
    else:
        stmt = select(Repository).where(Repository.name == repo_id_or_name)

    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Delete artifacts from DB
    art_stmt = select(Artifact).where(Artifact.repo_name == repo.name)
    art_res = await db.execute(art_stmt)
    artifacts = art_res.scalars().all()
    for art in artifacts:
        await db.delete(art)

    await db.delete(repo)
    await db.commit()
    return {"status": "success", "message": f"Repository {repo.name} deleted"}
