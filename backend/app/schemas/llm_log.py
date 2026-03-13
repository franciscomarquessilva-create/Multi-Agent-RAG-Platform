from datetime import datetime
from pydantic import BaseModel


class LLMLogResponse(BaseModel):
    id: str
    agent_id: str | None
    agent_name: str
    model: str
    request_payload: str
    response_payload: str | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
