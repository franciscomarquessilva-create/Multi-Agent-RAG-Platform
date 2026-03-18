from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, MeResponse
from app.services.auth_service import require_auth
from app.services.user_service import list_users, get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user):
    from fastapi import HTTPException
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/me", response_model=MeResponse)
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    user = await require_auth(request, db)
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        credits=user.credits,
        agent_limit=user.agent_limit,
        is_active=user.is_active,
        is_blocked=user.is_blocked,
    )


@router.get("", response_model=List[UserResponse])
async def list_users_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await list_users(db)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(user_id: str, data: UserUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await update_user(db, user_id, data)
