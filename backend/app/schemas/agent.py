from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=100)
    model: str = Field(..., max_length=100)
    api_key: str = Field(default="")
    use_default_key: bool = False
    agent_type: str = "slave"  # orchestrator | slave
    purpose: str = Field(default="", max_length=4000)
    instructions: str = Field(default="", max_length=8000)
    orchestrator_mode: Optional[str] = None  # broadcast | orchestrate | mediator
    allowed_slave_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("name", "model")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @model_validator(mode="after")
    def check_api_key_required(self) -> "AgentCreate":
        if not self.use_default_key:
            if not self.api_key or not self.api_key.strip():
                raise ValueError("api_key is required when not using the default key")
            self.api_key = self.api_key.strip()
        else:
            self.api_key = ""
        return self


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    api_key: Optional[str] = None
    use_default_key: Optional[bool] = None
    agent_type: Optional[str] = None
    purpose: Optional[str] = Field(default=None, max_length=4000)
    instructions: Optional[str] = Field(default=None, max_length=8000)
    orchestrator_mode: Optional[str] = None
    allowed_slave_ids: Optional[list[str]] = Field(default=None, max_length=50)

    @field_validator("name", "model")
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
    use_default_key: bool
    agent_type: str
    purpose: str
    instructions: str
    orchestrator_mode: Optional[str]
    allowed_slave_ids: list[str]
    is_orchestrator: bool
    created_at: datetime

    model_config = {"from_attributes": True}
