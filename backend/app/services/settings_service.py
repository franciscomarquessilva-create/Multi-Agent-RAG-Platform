import json
import base64
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.app_settings import AppSettings
from app.models.prompt_config import PromptConfig  # noqa: registers table with Base
from app.schemas.settings import AppSettingsResponse, ModelOption
from app.services.llm_service import normalize_model_name

logger = logging.getLogger(__name__)


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
    "mediator_default_purpose": {
        "value": (
            "Mediator orchestrator that runs a structured debate between two slave agents, "
            "decides speaking order each round, and produces a balanced final assessment."
        ),
        "description": "Default purpose text pre-filled when creating a mediator orchestrator agent.",
    },
    "mediator_default_instructions": {
        "value": (
            "Run a controlled discussion between exactly two slave agents around the user's discussion topic. "
            "The user may also give private mediator instructions that must not be revealed to the slaves. "
            "On each round, decide which agent should speak first based on the current state of the debate. "
            "At the end, summarize agreements, disagreements, and score each agent fairly."
        ),
        "description": "Default instructions pre-filled when creating a mediator orchestrator agent.",
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
    "mediator_orchestrator_system_prompt": {
        "value": (
            "You are {orchestrator_name}, the mediator orchestrator. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions} "
            "You must keep private mediator instructions hidden from the slave agents."
        ),
        "description": (
            "System prompt for the mediator orchestrator. "
            "Supports {orchestrator_name}, {purpose}, {instructions}."
        ),
    },
    "mediator_turn_selection_prompt": {
        "value": (
            "Decide which of the two agents should speak first in this round based on the topic, prior context, "
            "and the debate so far. Reply ONLY with a JSON array of the two agent names in speaking order, "
            "e.g. [\"AgentA\",\"AgentB\"]."
        ),
        "description": "Prompt sent to the mediator to decide round speaking order.",
    },
    "mediator_slave_system_prompt": {
        "value": (
            "You are {agent_name}. "
            "Purpose: {purpose}. "
            "Behaviour instructions: {instructions} "
            "You are participating in a mediated debate against {opponent_name}. "
            "Respond only to the debate topic and visible debate transcript."
        ),
        "description": (
            "System prompt for a slave agent during a mediated debate. "
            "Supports {agent_name}, {purpose}, {instructions}, {opponent_name}."
        ),
    },
    "mediator_final_synthesis_prompt": {
        "value": (
            "Using the debate transcript above, produce a final mediation report with these sections: "
            "Agreements, Disagreements, Scores, and Final Assessment. "
            "Scores should be numeric and justified briefly for each agent."
        ),
        "description": "Instruction appended when the mediator produces the final report.",
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
SETTINGS_ROW_ID = "default"


def _serialize_model_options(options: list[ModelOption]) -> str:
    return json.dumps([option.model_dump() for option in options])


# ---------------------------------------------------------------------------
# Fernet encryption helpers for default API keys
# ---------------------------------------------------------------------------

def _get_fernet():
    from cryptography.fernet import Fernet
    from app.config import get_settings
    key = get_settings().secret_key
    if not key:
        raise ValueError("SECRET_KEY is not configured")
    try:
        return Fernet(key.encode())
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        return Fernet(derived)


def _encrypt_default_key(api_key: str) -> str:
    return _get_fernet().encrypt(api_key.encode()).decode()


def _decrypt_default_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def _get_raw_default_keys(row: AppSettings) -> dict[str, str]:
    """Return {model: encrypted_key} from the settings row."""
    raw = getattr(row, "default_api_keys_json", None) or "{}"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
def _parse_model_options(raw: str | None) -> list[ModelOption]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return []
        options: list[ModelOption] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if "enabled" not in item:
                item["enabled"] = True
            options.append(ModelOption(**item))
        return options
    except Exception:
        return []


def _dedupe_options(options: list[ModelOption]) -> list[ModelOption]:
    seen: set[str] = set()
    deduped: list[ModelOption] = []
    for option in options:
        key = normalize_model_name(option.model)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            ModelOption(
                provider=option.provider.strip(),
                label=option.label.strip(),
                model=key,
                enabled=bool(option.enabled),
            )
        )
    return deduped


async def _get_or_create_settings_row(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.id == SETTINGS_ROW_ID))
    row = result.scalar_one_or_none()
    if row:
        return row

    row = AppSettings(
        id=SETTINGS_ROW_ID,
        available_models_json=_serialize_model_options(DEFAULT_MODEL_OPTIONS),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _ensure_model_catalog(db: AsyncSession, row: AppSettings) -> list[ModelOption]:
    options = _dedupe_options(_parse_model_options(getattr(row, "available_models_json", None)))
    if options:
        return options

    options = _dedupe_options(DEFAULT_MODEL_OPTIONS)
    row.available_models_json = _serialize_model_options(options)
    await db.commit()
    await db.refresh(row)
    return options


def _normalize_option(provider: str, label: str, model: str, enabled: bool = True) -> ModelOption:
    provider_clean = provider.strip()
    label_clean = label.strip()
    model_clean = normalize_model_name(model)
    if not provider_clean:
        raise HTTPException(status_code=400, detail="Provider is required")
    if not label_clean:
        raise HTTPException(status_code=400, detail="Label is required")
    if not model_clean:
        raise HTTPException(status_code=400, detail="Model identifier is required")
    return ModelOption(provider=provider_clean, label=label_clean, model=model_clean, enabled=bool(enabled))


async def get_app_settings(db: AsyncSession) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    available_models = await _ensure_model_catalog(db, row)
    default_key_providers = sorted(_get_raw_default_keys(row).keys())
    return AppSettingsResponse(
        available_models=available_models,
        credits_per_process=max(0, getattr(row, "credits_per_process", 1) or 1),
        default_key_providers=default_key_providers,
    )


async def update_app_settings(
    db: AsyncSession,
    credits_per_process: int | None = None,
) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    await _ensure_model_catalog(db, row)
    if credits_per_process is not None and credits_per_process >= 0:
        row.credits_per_process = max(0, credits_per_process)
    await db.commit()
    await db.refresh(row)
    return await get_app_settings(db)


async def list_available_models(db: AsyncSession) -> list[ModelOption]:
    row = await _get_or_create_settings_row(db)
    return await _ensure_model_catalog(db, row)


async def add_available_model(db: AsyncSession, *, provider: str, label: str, model: str, enabled: bool = True) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    options = await _ensure_model_catalog(db, row)
    new_option = _normalize_option(provider, label, model, enabled)

    if any(option.model == new_option.model for option in options):
        raise HTTPException(status_code=409, detail=f"Model '{new_option.model}' already exists")

    options.append(new_option)
    row.available_models_json = _serialize_model_options(options)
    await db.commit()
    return await get_app_settings(db)


async def update_available_model(
    db: AsyncSession,
    *,
    current_model: str,
    provider: str,
    label: str,
    model: str,
    enabled: bool,
) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    options = await _ensure_model_catalog(db, row)

    current_key = normalize_model_name(current_model)
    next_option = _normalize_option(provider, label, model, enabled)
    idx = next((i for i, option in enumerate(options) if option.model == current_key), -1)
    if idx < 0:
        raise HTTPException(status_code=404, detail=f"Model '{current_key}' not found")

    if next_option.model != current_key:
        duplicate = any(option.model == next_option.model for option in options)
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Model '{next_option.model}' already exists")
        usage = await db.execute(select(Agent).where(Agent.model == current_key))
        if usage.scalars().first() is not None:
            raise HTTPException(status_code=400, detail="Cannot rename model identifier while it is used by existing agents")

    options[idx] = next_option
    options[idx].enabled = bool(enabled)
    row.available_models_json = _serialize_model_options(options)

    await db.commit()
    return await get_app_settings(db)


async def delete_available_model(db: AsyncSession, *, model: str) -> AppSettingsResponse:
    row = await _get_or_create_settings_row(db)
    options = await _ensure_model_catalog(db, row)

    key = normalize_model_name(model)
    if len(options) <= 1:
        raise HTTPException(status_code=400, detail="At least one model must remain in the catalog")

    option_exists = any(option.model == key for option in options)
    if not option_exists:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")

    usage = await db.execute(select(Agent).where(Agent.model == key))
    if usage.scalars().first() is not None:
        raise HTTPException(status_code=400, detail="Cannot remove model currently used by an existing agent")

    updated_options = [option for option in options if option.model != key]
    row.available_models_json = _serialize_model_options(updated_options)

    await db.commit()
    return await get_app_settings(db)


async def is_model_enabled(db: AsyncSession, model: str) -> bool:
    normalized = normalize_model_name(model)
    settings = await get_app_settings(db)
    for option in settings.available_models:
        if option.model == normalized:
            return bool(option.enabled)
    return False


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
                updated_at=datetime.now(timezone.utc),
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
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.value = value
        row.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Default API key management (per provider, stored encrypted in AppSettings)
# ---------------------------------------------------------------------------

def _normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def provider_from_model(model: str) -> str:
    normalized = normalize_model_name(model)
    if "/" in normalized:
        provider, _ = normalized.split("/", 1)
        return _normalize_provider(provider)
    return _normalize_provider(normalized)

async def get_default_api_keys_map(db: AsyncSession) -> dict[str, str]:
    """Return {provider: decrypted_key} for providers with a default key configured."""
    row = await _get_or_create_settings_row(db)
    raw_map = _get_raw_default_keys(row)
    result: dict[str, str] = {}
    for provider_key, enc_key in raw_map.items():
        try:
            result[provider_key] = _decrypt_default_key(enc_key)
        except Exception:
            logger.warning("Failed to decrypt default API key for provider %s", provider_key)
    return result


async def set_default_api_key(db: AsyncSession, *, provider: str, api_key: str) -> AppSettingsResponse:
    """Store an encrypted default API key for the given provider."""
    row = await _get_or_create_settings_row(db)
    options = await _ensure_model_catalog(db, row)
    keys_map = _get_raw_default_keys(row)
    provider_key = _normalize_provider(provider)
    if not provider_key:
        raise HTTPException(status_code=400, detail="Provider is required")
    known_providers = {_normalize_provider(option.provider) for option in options}
    if provider_key not in known_providers:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider_key}'")
    if not api_key or not api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    keys_map[provider_key] = _encrypt_default_key(api_key.strip())
    row.default_api_keys_json = json.dumps(keys_map)
    await db.commit()
    return await get_app_settings(db)


async def delete_default_api_key(db: AsyncSession, *, provider: str) -> AppSettingsResponse:
    """Remove the default API key for the given provider."""
    row = await _get_or_create_settings_row(db)
    keys_map = _get_raw_default_keys(row)
    provider_key = _normalize_provider(provider)
    keys_map.pop(provider_key, None)
    row.default_api_keys_json = json.dumps(keys_map)
    await db.commit()
    return await get_app_settings(db)


async def get_credits_per_process(db: AsyncSession) -> int:
    """Return the currently configured credits consumed per agent LLM call."""
    row = await _get_or_create_settings_row(db)
    return max(0, getattr(row, "credits_per_process", 1) or 1)
