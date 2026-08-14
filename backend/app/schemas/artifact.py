import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_name: str
    path: str
    filename: str
    size_bytes: int
    content_type: str
    sha1: Optional[str] = None
    md5: Optional[str] = None
    sha256: Optional[str] = None
    is_cached_proxy: bool
    downloads_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_downloaded_at: Optional[datetime.datetime] = None

class FileTreeNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    size_bytes: Optional[int] = 0
    updated_at: Optional[str] = None
    sha1: Optional[str] = None
    md5: Optional[str] = None
    sha256: Optional[str] = None
    is_cached_proxy: Optional[bool] = False
    children: Optional[List['FileTreeNode']] = None

FileTreeNode.model_rebuild()

class FilePreviewResponse(BaseModel):
    filename: str
    path: str
    content_type: str
    size_bytes: int
    content: str  # text content or base64 indicator
    is_text: bool
