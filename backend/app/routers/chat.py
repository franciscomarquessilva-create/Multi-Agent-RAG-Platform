from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
import json
from datetime import datetime

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import ChatRequest
from app.services.orchestrator import handle_slave_broadcast, handle_orchestrator_mode

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send")
async def send_message(request: Request, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Validate conversation exists
    result = await db.execute(select(Conversation).where(Conversation.id == data.conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_msg = Message(
        conversation_id=data.conversation_id,
        role="user",
        content=data.content,
        mode=data.mode,
    )
    db.add(user_msg)

    # Update conversation title if it's still default
    if conv.title == "New Conversation":
        conv.title = data.content[:50] + ("..." if len(data.content) > 50 else "")
    conv.updated_at = datetime.utcnow()
    await db.commit()

    # Determine slave agent IDs
    slave_ids = data.agent_ids or conv.agent_ids
    # Remove orchestrator from slave list if present
    from app.services.agent_service import get_orchestrator
    try:
        orch = await get_orchestrator(db)
        slave_ids = [aid for aid in slave_ids if aid != orch.id]
    except Exception:
        pass

    collected_responses: list[dict] = []

    async def event_generator():
        nonlocal collected_responses

        if data.mode == "slave":
            gen = handle_slave_broadcast(db, data.content, slave_ids)
        else:
            gen = handle_orchestrator_mode(db, data.content, slave_ids if slave_ids else None)

        async for chunk in gen:
            # chunk is already "data: {...}\n\n"
            # Parse to collect for DB storage
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:].strip())
                    if not payload.get("done"):
                        collected_responses.append(payload)
                except Exception:
                    pass
            yield chunk

        # After streaming, save assistant messages to DB
        await _save_assistant_messages(db, data.conversation_id, data.mode, collected_responses)

    return EventSourceResponse(event_generator())


async def _save_assistant_messages(db, conversation_id: str, mode: str, responses: list[dict]):
    """Aggregate and save assistant messages."""
    from app.services.agent_service import get_orchestrator
    try:
        orch = await get_orchestrator(db)
        orch_id = orch.id
        orch_name = orch.name
    except Exception:
        orch_id = None
        orch_name = "Orchestrator"

    if mode == "slave":
        # Group by agent
        agent_chunks: dict[str, list[str]] = {}
        for r in responses:
            name = r.get("agent", "Unknown")
            agent_chunks.setdefault(name, []).append(r.get("content", ""))
        for agent_name, chunks in agent_chunks.items():
            full_content = "".join(chunks)
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
                mode=mode,
                agent_name=agent_name,
            )
            db.add(msg)
    else:
        # Orchestrator mode: single streamed response
        chunks = [r.get("content", "") for r in responses]
        full_content = "".join(chunks)
        msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
            mode=mode,
            agent_id=orch_id,
            agent_name=orch_name,
        )
        db.add(msg)

    await db.commit()
