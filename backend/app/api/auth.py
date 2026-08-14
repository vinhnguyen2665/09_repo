import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, generate_api_token
from app.core.rbac import get_current_user
from app.models.user import User, ApiToken, UserRole
from app.schemas.user import (
    LoginRequest, TokenResponse, UserOut,
    ApiTokenCreate, ApiTokenOut, ApiTokenCreatedResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == req.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role.value
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)

@router.get("/tokens", response_model=List[ApiTokenOut])
async def list_user_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApiToken).where(ApiToken.user_id == current_user.id).order_by(ApiToken.created_at.desc())
    res = await db.execute(stmt)
    tokens = res.scalars().all()
    return [ApiTokenOut.model_validate(t) for t in tokens]

@router.post("/tokens", response_model=ApiTokenCreatedResponse)
async def create_token(
    req: ApiTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    raw_token, prefix, token_hash = generate_api_token(current_user.id)
    token_obj = ApiToken(
        user_id=current_user.id,
        name=req.name,
        token_hash=token_hash,
        token_prefix=prefix,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(token_obj)
    await db.commit()
    await db.refresh(token_obj)

    return ApiTokenCreatedResponse(
        id=token_obj.id,
        name=token_obj.name,
        token_prefix=token_obj.token_prefix,
        created_at=token_obj.created_at,
        expires_at=token_obj.expires_at,
        raw_token=raw_token
    )

@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == current_user.id)
    res = await db.execute(stmt)
    token_obj = res.scalar_one_or_none()
    if not token_obj:
        raise HTTPException(status_code=404, detail="API Token not found")

    await db.delete(token_obj)
    await db.commit()
    return {"status": "success", "message": "Token revoked successfully"}
