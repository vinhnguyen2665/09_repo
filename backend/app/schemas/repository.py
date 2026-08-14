import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.repository import RepoFormat, RepoType

class RepositoryBase(BaseModel):
    name: str
    format: RepoFormat
    type: RepoType
    description: Optional[str] = ""
    is_online: bool = True
    upstream_url: Optional[str] = None
    cache_ttl_hours: Optional[int] = 720
    member_repo_names: Optional[List[str]] = []
    extra_config: Optional[Dict[str, Any]] = {}

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryUpdate(BaseModel):
    description: Optional[str] = None
    is_online: Optional[bool] = None
    upstream_url: Optional[str] = None
    cache_ttl_hours: Optional[int] = None
    member_repo_names: Optional[List[str]] = None
    extra_config: Optional[Dict[str, Any]] = None

class RepositoryOut(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    endpoint_url: Optional[str] = None
    total_artifacts: Optional[int] = 0
    total_size_bytes: Optional[int] = 0
