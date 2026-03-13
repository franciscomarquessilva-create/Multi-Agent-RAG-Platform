from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    orchestrator_id: str
    agent_ids: List[str] = Field(default_factory=list)


class ConversationTitleUpdate(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    orchestrator_id: str
    agent_ids: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            title=obj.title,
            orchestrator_id=obj.orchestrator_id,
            agent_ids=obj.agent_ids,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
