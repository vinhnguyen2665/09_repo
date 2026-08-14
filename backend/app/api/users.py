from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.rbac import require_admin, get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Users Management"])

@router.get("", response_model=List[UserOut])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).order_by(User.id.asc())
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [UserOut.model_validate(u) for u in users]

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where((User.username == req.username) | (User.email == req.email))
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=req.role,
        is_active=req.is_active
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserOut.model_validate(new_user)

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)

@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    req: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.email is not None:
        user.email = req.email
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password:
        user.hashed_password = get_password_hash(req.password)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": f"User {user.username} deleted"}
