from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate
from app.config import get_settings
from fastapi import HTTPException
import base64
import hashlib


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.secret_key
    if not key:
        # Generate a deterministic key from a default secret for development
        key = base64.urlsafe_b64encode(hashlib.sha256(b"dev-secret-key-change-me").digest()).decode()
    # Fernet keys must be 32 url-safe base64 bytes
    try:
        f = Fernet(key.encode())
    except Exception:
        # Derive proper key
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        f = Fernet(derived)
    return f


def encrypt_api_key(api_key: str) -> str:
    f = _get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
    # Check duplicate name
    result = await db.execute(select(Agent).where(Agent.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent with name '{data.name}' already exists")

    # Check if this is the first agent -> auto-set as orchestrator
    result_all = await db.execute(select(Agent))
    all_agents = result_all.scalars().all()
    is_first = len(all_agents) == 0

    agent = Agent(
        name=data.name,
        model=data.model,
        api_key_encrypted=encrypt_api_key(data.api_key),
        is_orchestrator=is_first,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def list_agents(db: AsyncSession) -> list[Agent]:
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
        # Check duplicate
        result = await db.execute(select(Agent).where(Agent.name == data.name, Agent.id != agent_id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Agent with name '{data.name}' already exists")
        agent.name = data.name
    if data.model is not None:
        agent.model = data.model
    if data.api_key is not None:
        agent.api_key_encrypted = encrypt_api_key(data.api_key)
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
    if agent.is_orchestrator:
        # Assign orchestrator to another agent
        other = next((a for a in all_agents if a.id != agent_id), None)
        if other:
            other.is_orchestrator = True
    await db.delete(agent)
    await db.commit()


async def set_orchestrator(db: AsyncSession, agent_id: str) -> Agent:
    # Unset current orchestrator
    result = await db.execute(select(Agent).where(Agent.is_orchestrator == True))
    current_orch = result.scalar_one_or_none()
    if current_orch:
        current_orch.is_orchestrator = False

    agent = await get_agent(db, agent_id)
    agent.is_orchestrator = True
    await db.commit()
    await db.refresh(agent)
    return agent


async def get_orchestrator(db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.is_orchestrator == True))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="No orchestrator configured")
    return agent
