from pydantic import BaseModel, Field


class ModelOption(BaseModel):
    provider: str
    label: str
    model: str


class ModelOptionCreate(BaseModel):
    provider: str
    label: str
    model: str


class ModelOptionUpdate(BaseModel):
    current_model: str
    provider: str
    label: str
    model: str


class AppSettingsResponse(BaseModel):
    allowed_models: list[str] = Field(default_factory=list)
    available_models: list[ModelOption] = Field(default_factory=list)


class AppSettingsUpdate(BaseModel):
    allowed_models: list[str] = Field(default_factory=list)


class PromptConfigItem(BaseModel):
    key: str
    value: str
    description: str

    model_config = {"from_attributes": True}


class PromptConfigUpdate(BaseModel):
    value: str
