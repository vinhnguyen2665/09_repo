import enum
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON, BigInteger
from app.core.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class RepoFormat(str, enum.Enum):
    MAVEN = "maven"
    NPM = "npm"
    DOCKER = "docker"
    PYPI = "pypi"

class RepoType(str, enum.Enum):
    HOSTED = "hosted"
    PROXY = "proxy"
    GROUP = "group"

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    format = Column(Enum(RepoFormat), nullable=False)
    type = Column(Enum(RepoType), nullable=False)
    description = Column(String(255), default="")
    is_online = Column(Boolean, default=True, nullable=False)
    
    # Proxy configuration
    upstream_url = Column(String(512), nullable=True)
    cache_ttl_hours = Column(Integer, default=720)  # 30 days default
    
    # Group configuration (ordered list of repository names)
    member_repo_names = Column(JSON, default=list)
    
    # Extra settings
    extra_config = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
