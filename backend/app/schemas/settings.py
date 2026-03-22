from pydantic import BaseModel, Field
from typing import Optional


class ModelOption(BaseModel):
    provider: str
    label: str
    model: str
    enabled: bool = True


class ModelOptionCreate(BaseModel):
    provider: str
    label: str
    model: str
    enabled: bool = True


class ModelOptionUpdate(BaseModel):
    current_model: str
    provider: str
    label: str
    model: str
    enabled: bool = True


class AppSettingsResponse(BaseModel):
    available_models: list[ModelOption] = Field(default_factory=list)
    credits_per_process: int = 1
    default_key_providers: list[str] = Field(default_factory=list)


class AppSettingsUpdate(BaseModel):
    credits_per_process: Optional[int] = None


class PromptConfigItem(BaseModel):
    key: str
    value: str
    description: str

    model_config = {"from_attributes": True}


class PromptConfigUpdate(BaseModel):
    value: str


class DefaultKeyUpdate(BaseModel):
    provider: str
    api_key: str
