from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    role: str
    content: str
    mode: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    mode: Optional[str]
    agent_id: Optional[str]
    agent_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: str
    content: str
    mode: str  # "orchestrator" or "slave"
    agent_ids: Optional[List[str]] = None  # slave agents to involve
