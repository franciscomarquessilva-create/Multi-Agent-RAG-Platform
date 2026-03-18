from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    credits: int
    agent_limit: int
    is_active: bool
    is_blocked: bool
    created_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: Optional[str] = None          # user | admin
    credits: Optional[int] = None       # absolute value
    credits_delta: Optional[int] = None # relative add/remove
    agent_limit: Optional[int] = None
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    credits: int
    agent_limit: int
    is_active: bool
    is_blocked: bool
