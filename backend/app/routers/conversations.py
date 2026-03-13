from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationTitleUpdate
from app.schemas.message import MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    import json

    # Orchestrator must be explicitly selected and must be of orchestrator type.
    orch_result = await db.execute(select(Agent).where(Agent.id == data.orchestrator_id))
    orchestrator = orch_result.scalar_one_or_none()
    if not orchestrator:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Orchestrator not found")
    if orchestrator.agent_type != "orchestrator":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only orchestrator agents can start a conversation")

    # Default selection is the orchestrator's associated slaves.
    selected_slave_ids = data.agent_ids or orchestrator.allowed_slave_ids

    # Validate selected participants are slave agents.
    if selected_slave_ids:
        slaves_result = await db.execute(select(Agent).where(Agent.id.in_(selected_slave_ids)))
        slave_map = {a.id: a for a in slaves_result.scalars().all()}
        missing = [sid for sid in selected_slave_ids if sid not in slave_map]
        if missing:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Slave agents not found: {', '.join(missing)}")
        invalid = [a.name for a in slave_map.values() if a.agent_type != "slave"]
        if invalid:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Only slave agents can be added: {', '.join(invalid)}")

    conv = Conversation(
        title=data.title or "New Conversation",
        orchestrator_id=orchestrator.id,
        agent_ids_json=json.dumps(selected_slave_ids),
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse.from_orm_obj(conv)


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    convs = result.scalars().all()
    return [ConversationResponse.from_orm_obj(c) for c in convs]


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()
    return {
        **ConversationResponse.from_orm_obj(conv).model_dump(),
        "messages": [MessageResponse.model_validate(m).model_dump() for m in messages],
    }


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()


@router.patch("/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, data: ConversationTitleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = data.title
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse.from_orm_obj(conv)
