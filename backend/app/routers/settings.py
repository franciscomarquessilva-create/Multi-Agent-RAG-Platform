from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.settings import (
    AppSettingsResponse,
    AppSettingsUpdate,
    ModelOption,
    ModelOptionCreate,
    ModelOptionUpdate,
    PromptConfigItem,
    PromptConfigUpdate,
)
from app.services.settings_service import (
    add_available_model,
    delete_available_model,
    get_app_settings,
    list_available_models,
    update_available_model,
    update_app_settings,
    get_all_prompt_configs,
    update_prompt_config,
)


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsResponse)
async def get_settings_endpoint(db: AsyncSession = Depends(get_db)):
    return await get_app_settings(db)


@router.put("", response_model=AppSettingsResponse)
async def update_settings_endpoint(data: AppSettingsUpdate, db: AsyncSession = Depends(get_db)):
    return await update_app_settings(db, data.allowed_models)


@router.get("/models", response_model=list[ModelOption])
async def list_models_endpoint(db: AsyncSession = Depends(get_db)):
    return await list_available_models(db)


@router.post("/models", response_model=AppSettingsResponse)
async def add_model_endpoint(data: ModelOptionCreate, db: AsyncSession = Depends(get_db)):
    return await add_available_model(db, provider=data.provider, label=data.label, model=data.model)


@router.put("/models", response_model=AppSettingsResponse)
async def update_model_endpoint(data: ModelOptionUpdate, db: AsyncSession = Depends(get_db)):
    return await update_available_model(
        db,
        current_model=data.current_model,
        provider=data.provider,
        label=data.label,
        model=data.model,
    )


@router.delete("/models", response_model=AppSettingsResponse)
async def delete_model_endpoint(model: str = Query(...), db: AsyncSession = Depends(get_db)):
    return await delete_available_model(db, model=model)


@router.get("/prompts", response_model=list[PromptConfigItem])
async def get_prompts_endpoint(db: AsyncSession = Depends(get_db)):
    rows = await get_all_prompt_configs(db)
    return [PromptConfigItem(key=r.key, value=r.value, description=r.description) for r in rows]


@router.put("/prompts/{key}", response_model=PromptConfigItem)
async def update_prompt_endpoint(key: str, data: PromptConfigUpdate, db: AsyncSession = Depends(get_db)):
    row = await update_prompt_config(db, key, data.value)
    return PromptConfigItem(key=row.key, value=row.value, description=row.description)
