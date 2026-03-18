from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.services.agent_service import (
    create_agent, list_agents, get_agent, update_agent, delete_agent, set_orchestrator
)
from app.services.auth_service import require_auth
from app.services.user_service import check_agent_limit

router = APIRouter(prefix="/agents", tags=["agents"])


def _check_ownership(agent, actor):
    """Raise 403 if non-admin actor doesn't own the agent."""
    if actor.role != "admin" and agent.owner_id != actor.id:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent_endpoint(data: AgentCreate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    await check_agent_limit(db, actor)
    return await create_agent(db, data, owner_id=actor.id)


@router.get("", response_model=List[AgentResponse])
async def list_agents_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    return await list_agents(db, actor)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    agent = await get_agent(db, agent_id)
    _check_ownership(agent, actor)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent_endpoint(agent_id: str, data: AgentUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    agent = await get_agent(db, agent_id)
    _check_ownership(agent, actor)
    return await update_agent(db, agent_id, data)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent_endpoint(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    agent = await get_agent(db, agent_id)
    _check_ownership(agent, actor)
    await delete_agent(db, agent_id)


@router.patch("/{agent_id}/orchestrator", response_model=AgentResponse)
async def set_orchestrator_endpoint(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    actor = await require_auth(request, db)
    agent = await get_agent(db, agent_id)
    _check_ownership(agent, actor)
    return await set_orchestrator(db, agent_id)
