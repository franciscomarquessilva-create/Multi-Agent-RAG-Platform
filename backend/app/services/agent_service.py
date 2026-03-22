from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate
from app.config import get_settings
from fastapi import HTTPException
import base64
import hashlib
from app.services.llm_service import normalize_model_name
from app.services.settings_service import is_model_allowed


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.secret_key
    if not key:
        raise ValueError(
            "SECRET_KEY is not configured. Set the SECRET_KEY environment variable before starting the application."
        )
    # Fernet keys must be 32 url-safe base64-encoded bytes; derive one if needed
    try:
        f = Fernet(key.encode())
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        f = Fernet(derived)
    return f


def encrypt_api_key(api_key: str) -> str:
    f = _get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def _validate_agent_type(agent_type: str) -> str:
    if agent_type not in {"orchestrator", "slave"}:
        raise HTTPException(status_code=400, detail="agent_type must be 'orchestrator' or 'slave'")
    return agent_type


def _validate_orchestrator_mode(mode: str | None) -> str:
    resolved = mode or "orchestrate"
    if resolved not in {"broadcast", "orchestrate", "mediator"}:
        raise HTTPException(status_code=400, detail="orchestrator_mode must be 'broadcast', 'orchestrate' or 'mediator'")
    return resolved


async def _validate_orchestrator_config(
    db: AsyncSession,
    allowed_slave_ids: list[str],
    orchestration_rules: list,
):
    # Ensure allowed targets are real slave agents.
    for sid in allowed_slave_ids:
        agent = await get_agent(db, sid)
        if agent.agent_type != "slave":
            raise HTTPException(status_code=400, detail=f"Agent '{agent.name}' is not a slave agent")

    allowed_set = set(allowed_slave_ids)
    for rule in orchestration_rules:
        slave_id = rule.get("slave_agent_id") if isinstance(rule, dict) else rule.slave_agent_id
        if slave_id not in allowed_set:
            raise HTTPException(
                status_code=400,
                detail="Every orchestration rule must target a slave listed in allowed_slave_ids",
            )
        rule_text = rule.get("rule", "") if isinstance(rule, dict) else rule.rule
        if not str(rule_text).strip():
            raise HTTPException(status_code=400, detail="Orchestration rule text cannot be empty")


async def create_agent(db: AsyncSession, data: AgentCreate, owner_id: str | None = None) -> Agent:
    # Check duplicate name scoped to this owner
    dup_q = select(Agent).where(Agent.name == data.name)
    if owner_id:
        dup_q = dup_q.where(Agent.owner_id == owner_id)
    result = await db.execute(dup_q)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent with name '{data.name}' already exists")

    agent_type = _validate_agent_type(data.agent_type)
    normalized_model = normalize_model_name(data.model)
    if not await is_model_allowed(db, normalized_model):
        raise HTTPException(status_code=400, detail=f"Model '{normalized_model}' is not enabled in settings")

    # Check if this is the first agent for this owner -> force orchestrator
    first_q = select(Agent).where(Agent.owner_id == owner_id) if owner_id else select(Agent)
    result_all = await db.execute(first_q)
    all_agents = result_all.scalars().all()
    is_first = len(all_agents) == 0
    if is_first:
        agent_type = "orchestrator"

    if agent_type == "orchestrator":
        await _validate_orchestrator_config(db, data.allowed_slave_ids, data.orchestration_rules)

    agent = Agent(
        name=data.name,
        model=normalized_model,
        api_key_encrypted=encrypt_api_key(data.api_key) if not data.use_default_key else encrypt_api_key(""),
        agent_type=agent_type,
        purpose=data.purpose,
        instructions=data.instructions,
        orchestrator_mode=_validate_orchestrator_mode(data.orchestrator_mode) if agent_type == "orchestrator" else "orchestrate",
        is_orchestrator=(agent_type == "orchestrator"),
        owner_id=owner_id,
    )
    agent.use_default_key = data.use_default_key
    agent.allowed_slave_ids = data.allowed_slave_ids if agent_type == "orchestrator" else []
    agent.orchestration_rules = [r.model_dump() for r in data.orchestration_rules] if agent_type == "orchestrator" else []
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def list_agents(db: AsyncSession, actor=None) -> list[Agent]:
    from app.models.user import User
    if actor and isinstance(actor, User) and actor.role != "admin":
        result = await db.execute(
            select(Agent).where(Agent.owner_id == actor.id).order_by(Agent.created_at)
        )
    else:
        result = await db.execute(select(Agent).order_by(Agent.created_at))
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: str) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def update_agent(db: AsyncSession, agent_id: str, data: AgentUpdate) -> Agent:
    agent = await get_agent(db, agent_id)
    if data.name is not None:
        # Check duplicate scoped to same owner
        dup_q = select(Agent).where(Agent.name == data.name, Agent.id != agent_id)
        if agent.owner_id:
            dup_q = dup_q.where(Agent.owner_id == agent.owner_id)
        result = await db.execute(dup_q)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Agent with name '{data.name}' already exists")
        agent.name = data.name
    if data.model is not None:
        normalized_model = normalize_model_name(data.model)
        if not await is_model_allowed(db, normalized_model):
            raise HTTPException(status_code=400, detail=f"Model '{normalized_model}' is not enabled in settings")
        agent.model = normalized_model
    if data.api_key is not None:
        agent.api_key_encrypted = encrypt_api_key(data.api_key)

    if data.use_default_key is not None:
        agent.use_default_key = data.use_default_key
        if data.use_default_key:
            # When switching to default key, clear stored key
            agent.api_key_encrypted = encrypt_api_key("")

    if not (agent.model or "").strip():
        raise HTTPException(status_code=400, detail="model is required")
    # Require api_key only when not using default key
    if not agent.use_default_key and not (agent.api_key_encrypted or "").strip():
        raise HTTPException(status_code=400, detail="api_key is required")

    next_type = _validate_agent_type(data.agent_type) if data.agent_type is not None else agent.agent_type

    if data.purpose is not None:
        agent.purpose = data.purpose
    if data.instructions is not None:
        agent.instructions = data.instructions

    if next_type == "orchestrator":
        if data.allowed_slave_ids is not None or data.orchestration_rules is not None:
            allowed = data.allowed_slave_ids if data.allowed_slave_ids is not None else agent.allowed_slave_ids
            rules = data.orchestration_rules if data.orchestration_rules is not None else agent.orchestration_rules
            await _validate_orchestrator_config(db, allowed, rules)
            agent.allowed_slave_ids = allowed
            if data.orchestration_rules is not None:
                agent.orchestration_rules = [r.model_dump() for r in data.orchestration_rules]
        if data.orchestrator_mode is not None:
            agent.orchestrator_mode = _validate_orchestrator_mode(data.orchestrator_mode)
        elif not agent.orchestrator_mode:
            agent.orchestrator_mode = "orchestrate"

        agent.agent_type = "orchestrator"
        agent.is_orchestrator = True
    else:
        agent.agent_type = "slave"
        agent.is_orchestrator = False
        agent.orchestrator_mode = "orchestrate"
        agent.allowed_slave_ids = []
        agent.orchestration_rules = []

    await db.commit()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, agent_id: str):
    # Ensure at least one agent remains
    result_all = await db.execute(select(Agent))
    all_agents = result_all.scalars().all()
    if len(all_agents) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last agent")
    agent = await get_agent(db, agent_id)
    await db.delete(agent)
    await db.commit()


async def set_orchestrator(db: AsyncSession, agent_id: str) -> Agent:
    agent = await get_agent(db, agent_id)
    agent.agent_type = "orchestrator"
    agent.is_orchestrator = True
    if not agent.orchestrator_mode:
        agent.orchestrator_mode = "orchestrate"
    await db.commit()
    await db.refresh(agent)
    return agent


async def get_orchestrator(db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.agent_type == "orchestrator").order_by(Agent.created_at))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="No orchestrator configured")
    return agent


async def get_orchestrator_by_id(db: AsyncSession, agent_id: str) -> Agent:
    agent = await get_agent(db, agent_id)
    if agent.agent_type != "orchestrator":
        raise HTTPException(status_code=400, detail="Selected agent is not an orchestrator")
    return agent
