import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Index
from app.core.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(64), index=True, nullable=False)
    path = Column(String(1024), index=True, nullable=False)
    filename = Column(String(255), index=True, nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    content_type = Column(String(128), default="application/octet-stream", nullable=False)
    
    sha1 = Column(String(64), nullable=True)
    md5 = Column(String(64), nullable=True)
    sha256 = Column(String(64), nullable=True)
    
    is_cached_proxy = Column(Boolean, default=False, nullable=False)
    downloads_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_repo_path", "repo_name", "path", unique=True),
    )
