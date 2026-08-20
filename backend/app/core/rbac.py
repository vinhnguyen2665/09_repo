import base64
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPBasic, HTTPBasicCredentials, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, verify_password, hash_token
from app.models.user import User, ApiToken, UserRole

bearer_scheme = HTTPBearer(auto_error=False)
basic_scheme = HTTPBasic(auto_error=False)

async def authenticate_user_from_request(
    request: Request,
    db: AsyncSession
) -> Optional[User]:
    """
    Authenticate user via:
    1. Bearer JWT or API Token in Authorization header
    2. Basic Auth in Authorization header (username:password or username:api_token)
    3. Custom X-API-Token header
    """
    auth_header = request.headers.get("Authorization")
    api_token_header = request.headers.get("X-API-Token")

    # 1. Custom Header X-API-Token
    if api_token_header:
        token_hash = hash_token(api_token_header.strip())
        stmt = select(ApiToken).where(ApiToken.token_hash == token_hash)
        res = await db.execute(stmt)
        api_token_obj = res.scalar_one_or_none()
        if api_token_obj:
            user_stmt = select(User).where(User.id == api_token_obj.user_id, User.is_active == True)
            user_res = await db.execute(user_stmt)
            return user_res.scalar_one_or_none()

    if not auth_header:
        return None

    # 2. Bearer Authentication
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        # First try JWT
        payload = decode_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            # sub can be username or id
            if str(user_id).isdigit():
                stmt = select(User).where(User.id == int(user_id), User.is_active == True)
            else:
                stmt = select(User).where(User.username == str(user_id), User.is_active == True)
            res = await db.execute(stmt)
            user = res.scalar_one_or_none()
            if user:
                return user

        # Next check if it's an API token (starts with z9r_)
        token_hash = hash_token(token)
        stmt = select(ApiToken).where(ApiToken.token_hash == token_hash)
        res = await db.execute(stmt)
        api_token_obj = res.scalar_one_or_none()
        if api_token_obj:
            user_stmt = select(User).where(User.id == api_token_obj.user_id, User.is_active == True)
            user_res = await db.execute(user_stmt)
            return user_res.scalar_one_or_none()

    # 3. Basic Authentication
    if auth_header.startswith("Basic "):
        try:
            encoded_credentials = auth_header[6:].strip()
            decoded = base64.b64decode(encoded_credentials).decode("utf-8")
            if ":" in decoded:
                username, password = decoded.split(":", 1)
                
                # Check if password is an API token
                if password.startswith("z9r_"):
                    token_hash = hash_token(password)
                    stmt = select(ApiToken).where(ApiToken.token_hash == token_hash)
                    res = await db.execute(stmt)
                    api_token_obj = res.scalar_one_or_none()
                    if api_token_obj:
                        user_stmt = select(User).where(User.id == api_token_obj.user_id, User.is_active == True)
                        user_res = await db.execute(user_stmt)
                        return user_res.scalar_one_or_none()

                # Check if username is __token__ and password is api token (twine convention)
                if username == "__token__":
                    token_hash = hash_token(password)
                    stmt = select(ApiToken).where(ApiToken.token_hash == token_hash)
                    res = await db.execute(stmt)
                    api_token_obj = res.scalar_one_or_none()
                    if api_token_obj:
                        user_stmt = select(User).where(User.id == api_token_obj.user_id, User.is_active == True)
                        user_res = await db.execute(user_stmt)
                        return user_res.scalar_one_or_none()

                # Normal username & password check
                stmt = select(User).where(User.username == username, User.is_active == True)
                res = await db.execute(stmt)
                user = res.scalar_one_or_none()
                if user and verify_password(password, user.hashed_password):
                    return user
        except Exception:
            return None

    return None

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    return await authenticate_user_from_request(request, db)

def require_role(allowed_roles: list[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in allowed_roles]}",
            )
        return current_user
    return role_checker

require_admin = require_role([UserRole.ADMIN])
require_developer = require_role([UserRole.ADMIN, UserRole.DEVELOPER])
require_reader = require_role([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.READER])
