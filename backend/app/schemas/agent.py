from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AgentCreate(BaseModel):
    name: str
    model: str
    api_key: str


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    model: str
    is_orchestrator: bool
    created_at: datetime

    model_config = {"from_attributes": True}
