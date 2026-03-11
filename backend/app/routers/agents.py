from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.services.agent_service import (
    create_agent, list_agents, get_agent, update_agent, delete_agent, set_orchestrator
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent_endpoint(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    return await create_agent(db, data)


@router.get("", response_model=List[AgentResponse])
async def list_agents_endpoint(db: AsyncSession = Depends(get_db)):
    return await list_agents(db)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(agent_id: str, db: AsyncSession = Depends(get_db)):
    return await get_agent(db, agent_id)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent_endpoint(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    return await update_agent(db, agent_id, data)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent_endpoint(agent_id: str, db: AsyncSession = Depends(get_db)):
    await delete_agent(db, agent_id)


@router.patch("/{agent_id}/orchestrator", response_model=AgentResponse)
async def set_orchestrator_endpoint(agent_id: str, db: AsyncSession = Depends(get_db)):
    return await set_orchestrator(db, agent_id)
