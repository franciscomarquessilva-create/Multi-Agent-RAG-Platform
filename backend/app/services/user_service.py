from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.user import User
from app.models.agent import Agent
from app.schemas.user import UserUpdate
from app.config import get_settings


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_user(db: AsyncSession, user_id: str, data: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)

    if data.role is not None:
        if data.role not in {"user", "admin"}:
            raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'")
        user.role = data.role

    if data.credits is not None:
        user.credits = max(0, data.credits)

    if data.credits_delta is not None:
        user.credits = max(0, user.credits + data.credits_delta)

    if data.agent_limit is not None:
        user.agent_limit = data.agent_limit  # -1 = unlimited

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.is_blocked is not None:
        user.is_blocked = data.is_blocked

    await db.commit()
    await db.refresh(user)
    return user


async def count_user_agents(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count()).where(Agent.owner_id == user_id)
    )
    return result.scalar_one()


async def check_agent_limit(db: AsyncSession, user: User) -> None:
    """Raise HTTP 403 if user is at or above their agent limit."""
    if user.agent_limit == -1:
        return  # unlimited
    count = await count_user_agents(db, user.id)
    if count >= user.agent_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Agent limit reached ({user.agent_limit}). Delete an agent or ask an admin to increase your limit.",
        )


async def deduct_credits(db: AsyncSession, user: User, amount: int) -> None:
    """Deduct credits from user. Raises 402 if insufficient."""
    if user.role == "admin":
        return  # admins have unlimited credits
    if user.credits < amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You have {user.credits} and need {amount}.",
        )
    user.credits -= amount
    await db.commit()


async def deduct_credits_soft(db: AsyncSession, user_id: str, amount: int) -> None:
    """Deduct credits from user without raising. Clamps to zero. Skips admin users."""
    from app.models.user import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.role == "admin":
        return
    user.credits = max(0, user.credits - amount)
    await db.commit()
