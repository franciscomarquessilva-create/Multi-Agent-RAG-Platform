from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.schemas.message import MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    import json
    conv = Conversation(
        title=data.title or "New Conversation",
        agent_ids_json=json.dumps(data.agent_ids),
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
async def update_conversation_title(conversation_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = data.get("title", conv.title)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse.from_orm_obj(conv)
