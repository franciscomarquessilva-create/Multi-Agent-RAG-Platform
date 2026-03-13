import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.prompt_config import PromptConfig  # noqa: registers table with Base
from app.schemas.settings import AppSettingsResponse, ModelOption
from app.services.llm_service import normalize_model_name


# ---------------------------------------------------------------------------
# Default prompts – these are seeded into the DB on first access
# ---------------------------------------------------------------------------

PROMPT_DEFAULTS: dict[str, dict] = {
    "broadcast_default_purpose": {
        "value": (
            "Broadcast orchestrator that distributes the same message to all slave agents "
            "simultaneously whenever Broadcast instructions are provided, then aggregates their responses."
        ),
        "description": "Default purpose text pre-filled when creating a broadcast orchestrator agent.",
    },
    "broadcast_default_instructions": {
        "value": (
            "When Broadcast instructions are provided, send only those instructions to every slave agent. "
            "Do not require any extra keyword or explicit request in the user's text to trigger the broadcast. "
            "Collect all responses and follow the user's instructions on what to do with them "
            "(summarise, compare, list, aggregate, etc.). "
            "If no Broadcast instructions are provided, answer directly without involving slave agents."
        ),
        "description": "Default instructions pre-filled when creating a broadcast orchestrator agent.",
    },
    "orchestrate_default_purpose": {
        "value": (
            "Orchestrator that coordinates specialised agents by discovering their expertise "
            "and sequencing tasks to resolve complex user requests."
        ),
        "description": "Default purpose text pre-filled when creating an orchestrate orchestrator agent.",
    },
    "orchestrate_default_instructions": {
        "value": (
            "In the first step, ask each available slave agent to describe their specialisation and capabilities. "
            "Based on their responses, build a resolution plan that sequences tasks to the most relevant agents, "
            "using each agent's output as input for the next. "
            "Agents with no relevant specialisation for the current task should be skipped. "
            "When the final output is ready, follow the user's instructions on how to present or process the result."
        ),
        "description": "Default instructions pre-filled when creating an orchestrate orchestrator agent.",
    },
    "broadcast_slave_system_prompt": {
        "value": (
            "You are {agent_name}. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions}"
        ),
        "description": (
            "System prompt template for slave agents during a broadcast. "
            "Supports {agent_name}, {purpose}, {instructions}."
        ),
    },
    "broadcast_aggregation_system_prompt": {
        "value": (
            "You are {orchestrator_name}. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions} "
            "You have just received responses from all slave agents listed below. "
            "Follow the user's original instructions about what to do with these responses."
        ),
        "description": (
            "System prompt for broadcast orchestrator when aggregating slave responses. "
            "Supports {orchestrator_name}, {purpose}, {instructions}."
        ),
    },
    "orchestrate_speciality_query": {
        "value": (
            "Describe your specialisation and capabilities in 2–3 sentences. "
            "What types of tasks are you best suited for? Be concise."
        ),
        "description": "Message sent to each slave agent in the discovery round to learn their specialisation.",
    },
    "orchestrate_plan_request": {
        "value": (
            "Given the agent specialisations above and the user's request, decide which agents are relevant "
            "and in what order they should be called to best resolve the request. "
            "Use each agent's output as input for the next. "
            "Agents with no relevant specialisation for the current task should be excluded. "
            "Reply ONLY with a JSON array of agent names in execution order, "
            "e.g. [\"Agent1\",\"Agent2\"]. If no agents are relevant, return []."
        ),
        "description": (
            "Prompt sent to the orchestrator to produce a sequenced execution plan "
            "as a JSON array of agent names."
        ),
    },
    "orchestrate_slave_task_system_prompt": {
        "value": (
            "You are {agent_name}. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions} "
            "You are operating as part of a multi-agent pipeline. "
            "Complete your assigned task and return a clear, concise result."
        ),
        "description": (
            "System prompt for slave agents during sequential task execution. "
            "Supports {agent_name}, {purpose}, {instructions}."
        ),
    },
    "orchestrate_orchestrator_system_prompt": {
        "value": (
            "You are {orchestrator_name}, the main orchestrator AI assistant. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions} "
            "You coordinate multiple AI agents to resolve complex user tasks."
        ),
        "description": (
            "System prompt for the orchestrate orchestrator. "
            "Supports {orchestrator_name}, {purpose}, {instructions}."
        ),
    },
    "orchestrate_final_synthesis_prompt": {
        "value": (
            "Based on the entire collaboration output above, "
            "provide a comprehensive final answer to the user's original request."
        ),
        "description": "Instruction appended when generating the orchestrator's final answer.",
    },
}


DEFAULT_MODEL_OPTIONS: list[ModelOption] = [
    ModelOption(provider="OpenAI", label="GPT-5.2", model="openai/gpt-5.2"),
    ModelOption(provider="OpenAI", label="GPT-5.1", model="openai/gpt-5.1"),
    ModelOption(provider="OpenAI", label="GPT-4o", model="openai/gpt-4o"),
    ModelOption(provider="Anthropic", label="Claude 3.7 Sonnet", model="anthropic/claude-3-7-sonnet"),
    ModelOption(provider="Anthropic", label="Claude 3.5 Sonnet", model="anthropic/claude-3-5-sonnet"),
    ModelOption(provider="Anthropic", label="Claude 3.5 Haiku", model="anthropic/claude-3-5-haiku"),
    ModelOption(provider="Gemini", label="Gemini 2.0 Flash", model="gemini/gemini-2.0-flash"),
    ModelOption(provider="Gemini", label="Gemini 1.5 Pro", model="gemini/gemini-1.5-pro"),
    ModelOption(provider="Gemini", label="Gemini 1.5 Flash", model="gemini/gemini-1.5-flash"),
    ModelOption(provider="Grok", label="Grok 2", model="xai/grok-2"),
    ModelOption(provider="Grok", label="Grok 2 Latest", model="xai/grok-2-latest"),
]
DEFAULT_ALLOWED_MODELS = [
    "openai/gpt-5.2",
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet",
    "gemini/gemini-1.5-pro",
    "xai/grok-2",
]
SETTINGS_ROW_ID = "default"


async def _get_or_create_settings_row(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.id == SETTINGS_ROW_ID))
    row = result.scalar_one_or_none()
    if row:
        return row

    row = AppSettings(id=SETTINGS_ROW_ID, allowed_models_json=json.dumps(DEFAULT_ALLOWED_MODELS))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_app_settings(db: AsyncSession) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    allowed_models = json.loads(row.allowed_models_json or "[]")
    return AppSettingsResponse(
        allowed_models=allowed_models,
        available_models=DEFAULT_MODEL_OPTIONS,
    )


async def update_app_settings(db: AsyncSession, allowed_models: list[str]) -> AppSettingsResponse:
    normalized = [normalize_model_name(model) for model in allowed_models if model.strip()]
    allowed_set = {option.model for option in DEFAULT_MODEL_OPTIONS}
    invalid = [model for model in normalized if model not in allowed_set]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported models: {', '.join(invalid)}")
    if not normalized:
        raise HTTPException(status_code=400, detail="At least one model must be enabled")

    row = await _get_or_create_settings_row(db)
    row.allowed_models_json = json.dumps(normalized)
    await db.commit()
    await db.refresh(row)
    return await get_app_settings(db)


async def is_model_allowed(db: AsyncSession, model: str) -> bool:
    settings = await get_app_settings(db)
    return normalize_model_name(model) in set(settings.allowed_models)


# ---------------------------------------------------------------------------
# Prompt config CRUD
# ---------------------------------------------------------------------------

async def get_all_prompt_values(db: AsyncSession) -> dict[str, str]:
    """Return all prompt values, seeding missing defaults into the DB."""
    result = await db.execute(select(PromptConfig))
    rows: dict[str, str] = {row.key: row.value for row in result.scalars().all()}

    needs_commit = False
    for key, meta in PROMPT_DEFAULTS.items():
        if key not in rows:
            db.add(PromptConfig(
                key=key,
                value=meta["value"],
                description=meta["description"],
                updated_at=datetime.utcnow(),
            ))
            rows[key] = meta["value"]
            needs_commit = True
    if needs_commit:
        await db.commit()

    return rows


async def get_all_prompt_configs(db: AsyncSession) -> list[PromptConfig]:
    """Return all prompt config rows (seeds defaults if missing)."""
    await get_all_prompt_values(db)
    result = await db.execute(select(PromptConfig))
    allowed_keys = set(PROMPT_DEFAULTS.keys())
    configs = [row for row in result.scalars().all() if row.key in allowed_keys]
    # Return in a stable order: follow PROMPT_DEFAULTS key order, then any extras
    key_order = list(PROMPT_DEFAULTS.keys())
    return sorted(configs, key=lambda c: key_order.index(c.key) if c.key in key_order else len(key_order))


async def update_prompt_config(db: AsyncSession, key: str, value: str) -> PromptConfig:
    """Update a single prompt config value."""
    if key not in PROMPT_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown prompt key: {key}")

    result = await db.execute(select(PromptConfig).where(PromptConfig.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        row = PromptConfig(
            key=key,
            value=value,
            description=PROMPT_DEFAULTS[key]["description"],
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    else:
        row.value = value
        row.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(row)
    return row
