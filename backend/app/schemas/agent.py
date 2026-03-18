from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class OrchestrationRule(BaseModel):
    slave_agent_id: str
    rule: str


class AgentCreate(BaseModel):
    name: str
    model: str
    api_key: str
    agent_type: str = "slave"  # orchestrator | slave
    purpose: str = ""
    instructions: str = ""
    orchestrator_mode: Optional[str] = None  # broadcast | orchestrate | mediator
    allowed_slave_ids: list[str] = Field(default_factory=list)
    orchestration_rules: list[OrchestrationRule] = Field(default_factory=list)

    @field_validator("name", "model", "api_key")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    agent_type: Optional[str] = None
    purpose: Optional[str] = None
    instructions: Optional[str] = None
    orchestrator_mode: Optional[str] = None
    allowed_slave_ids: Optional[list[str]] = None
    orchestration_rules: Optional[list[OrchestrationRule]] = None

    @field_validator("name", "model", "api_key")
    @classmethod
    def validate_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned


class AgentResponse(BaseModel):
    id: str
    name: str
    model: str
    agent_type: str
    purpose: str
    instructions: str
    orchestrator_mode: Optional[str]
    allowed_slave_ids: list[str]
    orchestration_rules: list[OrchestrationRule]
    is_orchestrator: bool
    created_at: datetime

    model_config = {"from_attributes": True}
