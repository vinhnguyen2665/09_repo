import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole

class UserBase(BaseModel):
    username: str
    email: str
    role: UserRole = UserRole.DEVELOPER
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class LoginRequest(BaseModel):
    username: str
    password: str

class ApiTokenCreate(BaseModel):
    name: str

class ApiTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token_prefix: str
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None

class ApiTokenCreatedResponse(ApiTokenOut):
    raw_token: str  # Only returned once upon creation
