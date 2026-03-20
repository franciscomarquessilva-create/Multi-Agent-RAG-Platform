from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    role: str
    content: str = Field(..., max_length=32000)
    message_type: str = "chat"
    mode: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    message_type: str
    mode: Optional[str]
    agent_id: Optional[str]
    agent_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: str
    content: str = Field(..., max_length=32000)
    mode: Optional[str] = "orchestrator"  # kept for backward compatibility
    agent_ids: Optional[List[str]] = None  # deprecated; conversation agent_ids are used
    broadcast_instructions: Optional[str] = Field(default=None, max_length=8000)
    orchestrator_instructions: Optional[str] = Field(default=None, max_length=8000)
    iterations: int = Field(default=1, ge=1, le=10)
