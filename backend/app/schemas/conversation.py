from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    agent_ids: List[str] = []


class ConversationResponse(BaseModel):
    id: str
    title: str
    agent_ids: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            title=obj.title,
            agent_ids=obj.agent_ids,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
