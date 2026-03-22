from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.settings import (
    AppSettingsResponse,
    AppSettingsUpdate,
    DefaultKeyUpdate,
    ModelOption,
    ModelOptionCreate,
    ModelOptionUpdate,
    PromptConfigItem,
    PromptConfigUpdate,
)
from app.services.auth_service import require_auth
from app.services.settings_service import (
    add_available_model,
    delete_available_model,
    delete_default_api_key,
    get_app_settings,
    list_available_models,
    set_default_api_key,
    update_available_model,
    update_app_settings,
    get_all_prompt_configs,
    update_prompt_config,
)


router = APIRouter(prefix="/settings", tags=["settings"])


def _require_admin(actor):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=AppSettingsResponse)
async def get_settings_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await get_app_settings(db)


@router.put("", response_model=AppSettingsResponse)
async def update_settings_endpoint(data: AppSettingsUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await update_app_settings(db, credits_per_process=data.credits_per_process)


@router.post("/default-keys", response_model=AppSettingsResponse)
async def set_default_key_endpoint(data: DefaultKeyUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await set_default_api_key(db, provider=data.provider, api_key=data.api_key)


@router.delete("/default-keys", response_model=AppSettingsResponse)
async def delete_default_key_endpoint(provider: str = Query(...), request: Request = None, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await delete_default_api_key(db, provider=provider)


@router.get("/models", response_model=list[ModelOption])
async def list_models_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await list_available_models(db)


@router.post("/models", response_model=AppSettingsResponse)
async def add_model_endpoint(data: ModelOptionCreate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await add_available_model(db, provider=data.provider, label=data.label, model=data.model, enabled=data.enabled)


@router.put("/models", response_model=AppSettingsResponse)
async def update_model_endpoint(data: ModelOptionUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await update_available_model(
        db,
        current_model=data.current_model,
        provider=data.provider,
        label=data.label,
        model=data.model,
        enabled=data.enabled,
    )


@router.delete("/models", response_model=AppSettingsResponse)
async def delete_model_endpoint(model: str = Query(...), request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    return await delete_available_model(db, model=model)


@router.get("/prompts", response_model=list[PromptConfigItem])
async def get_prompts_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    rows = await get_all_prompt_configs(db)
    return [PromptConfigItem(key=r.key, value=r.value, description=r.description) for r in rows]


@router.put("/prompts/{key}", response_model=PromptConfigItem)
async def update_prompt_endpoint(key: str, data: PromptConfigUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    _require_admin(actor)
    row = await update_prompt_config(db, key, data.value)
    return PromptConfigItem(key=row.key, value=row.value, description=row.description)
