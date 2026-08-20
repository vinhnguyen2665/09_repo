import enum
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, JSON, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    READER = "reader"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, native_enum=False), default=UserRole.DEVELOPER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    api_tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")

class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    token_prefix = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_tokens")
