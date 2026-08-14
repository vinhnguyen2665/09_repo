from typing import List, Dict, Any
from pydantic import BaseModel

class StorageStats(BaseModel):
    total_size_bytes: int
    private_hosted_bytes: int
    proxy_cached_bytes: int
    total_artifacts: int
    total_downloads: int
    total_repositories: int
    storage_free_bytes: int
    storage_total_bytes: int

class RepositoryStats(BaseModel):
    name: str
    format: str
    type: str
    artifacts_count: int
    total_size_bytes: int
    downloads_count: int

class RecentActivityItem(BaseModel):
    action: str  # "upload", "download", "cache_miss_fetched", "delete"
    repo_name: str
    artifact_path: str
    size_bytes: int
    timestamp: str

class SystemOverviewStats(BaseModel):
    storage: StorageStats
    repositories: List[RepositoryStats]
    recent_activity: List[RecentActivityItem]
