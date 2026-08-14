import shutil
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_reader
from app.models.artifact import Artifact
from app.models.repository import Repository
from app.models.user import User
from app.schemas.stats import (
    StorageStats, RepositoryStats, RecentActivityItem, SystemOverviewStats
)
from app.core.config import settings

router = APIRouter(prefix="/stats", tags=["Statistics & Monitoring"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Zero9Repo",
        "version": settings.VERSION
    }

@router.get("/overview", response_model=SystemOverviewStats)
async def get_overview_stats(
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    # Total disk space on host
    try:
        disk_usage = shutil.disk_usage(settings.BASE_DATA_DIR)
        total_disk = disk_usage.total
        free_disk = disk_usage.free
    except Exception:
        total_disk = 100 * 1024 * 1024 * 1024
        free_disk = 50 * 1024 * 1024 * 1024

    # Repos count
    repo_count_stmt = select(func.count(Repository.id))
    repo_count_res = await db.execute(repo_count_stmt)
    total_repos = repo_count_res.scalar_one() or 0

    # Artifact totals
    art_totals_stmt = select(
        func.count(Artifact.id),
        func.sum(Artifact.size_bytes),
        func.sum(Artifact.downloads_count)
    )
    art_totals_res = await db.execute(art_totals_stmt)
    total_arts, total_size, total_downloads = art_totals_res.first() or (0, 0, 0)
    total_arts = total_arts or 0
    total_size = total_size or 0
    total_downloads = total_downloads or 0

    # Hosted vs Proxy breakdown
    proxy_bytes_stmt = select(func.sum(Artifact.size_bytes)).where(Artifact.is_cached_proxy == True)
    proxy_bytes_res = await db.execute(proxy_bytes_stmt)
    proxy_cached_bytes = proxy_bytes_res.scalar_one() or 0

    private_hosted_bytes = max(0, total_size - proxy_cached_bytes)

    # Per repository stats
    repos_stmt = select(Repository).order_by(Repository.name.asc())
    repos_res = await db.execute(repos_stmt)
    repos = repos_res.scalars().all()

    repo_stats_list: List[RepositoryStats] = []
    for r in repos:
        r_stmt = select(
            func.count(Artifact.id),
            func.sum(Artifact.size_bytes),
            func.sum(Artifact.downloads_count)
        ).where(Artifact.repo_name == r.name)
        r_res = await db.execute(r_stmt)
        c, s, d = r_res.first() or (0, 0, 0)
        repo_stats_list.append(RepositoryStats(
            name=r.name,
            format=r.format.value,
            type=r.type.value,
            artifacts_count=c or 0,
            total_size_bytes=s or 0,
            downloads_count=d or 0
        ))

    # Recent activity
    recent_stmt = select(Artifact).order_by(Artifact.updated_at.desc()).limit(10)
    recent_res = await db.execute(recent_stmt)
    recent_artifacts = recent_res.scalars().all()

    recent_activity = [
        RecentActivityItem(
            action="cache_miss_fetched" if art.is_cached_proxy else "upload",
            repo_name=art.repo_name,
            artifact_path=art.path,
            size_bytes=art.size_bytes,
            timestamp=art.updated_at.isoformat()
        )
        for art in recent_artifacts
    ]

    return SystemOverviewStats(
        storage=StorageStats(
            total_size_bytes=total_size,
            private_hosted_bytes=private_hosted_bytes,
            proxy_cached_bytes=proxy_cached_bytes,
            total_artifacts=total_arts,
            total_downloads=total_downloads,
            total_repositories=total_repos,
            storage_free_bytes=free_disk,
            storage_total_bytes=total_disk
        ),
        repositories=repo_stats_list,
        recent_activity=recent_activity
    )
