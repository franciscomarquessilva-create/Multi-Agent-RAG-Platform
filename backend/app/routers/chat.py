from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import ChatRequest
from app.services.orchestrator import handle_orchestrator_mode
from app.services.auth_service import require_auth
from app.services.user_service import deduct_credits
from app.config import get_settings

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def _compose_user_content(data: ChatRequest, orchestrator_mode: str | None) -> str:
    if orchestrator_mode == "mediator":
        parts: list[str] = []
        if data.content.strip():
            parts.append(f"Discussion topic:\n{data.content.strip()}")
        if (data.orchestrator_instructions or "").strip():
            parts.append(f"Mediator instructions:\n{data.orchestrator_instructions.strip()}")
        return "\n\n".join(parts) if parts else data.content

    if orchestrator_mode != "broadcast":
        return data.content

    parts: list[str] = []
    if (data.broadcast_instructions or "").strip():
        parts.append(f"Broadcast instructions:\n{data.broadcast_instructions.strip()}")
    if (data.orchestrator_instructions or "").strip():
        parts.append(f"Orchestrator instructions:\n{data.orchestrator_instructions.strip()}")
    return "\n\n".join(parts) if parts else data.content


def _conversation_title_source(data: ChatRequest, orchestrator_mode: str | None) -> str:
    if orchestrator_mode == "mediator":
        return data.content.strip() or (data.orchestrator_instructions or "").strip() or data.content

    if orchestrator_mode == "broadcast":
        return (
            (data.orchestrator_instructions or "").strip()
            or (data.broadcast_instructions or "").strip()
            or data.content
        )
    return data.content


@router.post("/send")
async def send_message(request: Request, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Authenticate and check conversation ownership
    actor = await require_auth(request, db)

    # Validate conversation exists
    result = await db.execute(select(Conversation).where(Conversation.id == data.conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if actor.role != "admin" and conv.owner_id != actor.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Deduct credits before processing (admin exempt)
    cost = data.iterations * get_settings().credits_per_iteration
    await deduct_credits(db, actor, cost)

    orchestrator = None
    if conv.orchestrator_id:
        orch_result = await db.execute(select(Agent).where(Agent.id == conv.orchestrator_id))
        orchestrator = orch_result.scalar_one_or_none()

    # Guard old conversations that may have NULL/orphan orchestrator_id.
    if not orchestrator:
        fallback_result = await db.execute(
            select(Agent).where(Agent.agent_type == "orchestrator").order_by(Agent.created_at)
        )
        fallback = fallback_result.scalars().first()
        if fallback:
            orchestrator = fallback
            conv.orchestrator_id = fallback.id
            await db.commit()
            logger.warning("Repaired conversation %s with fallback orchestrator %s", conv.id, fallback.id)
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Conversation orchestrator is missing")

    if orchestrator.agent_type != "orchestrator":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Conversation orchestrator is invalid")

    # The user always talks to the conversation orchestrator.
    selected_slave_ids = list(conv.agent_ids)

    display_content = _compose_user_content(data, orchestrator.orchestrator_mode)

    # Resolve target label for chat history.
    target_label = f"Orchestrator: {orchestrator.name}"

    # Save user message.
    user_msg = Message(
        conversation_id=data.conversation_id,
        role="user",
        content=display_content,
        message_type="chat",
        mode="orchestrator",
        agent_name=target_label,
    )
    db.add(user_msg)

    # Update conversation title if it's still default
    if conv.title == "New Conversation":
        title_source = _conversation_title_source(data, orchestrator.orchestrator_mode)
        conv.title = title_source[:50] + ("..." if len(title_source) > 50 else "")
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    collected_responses: list[dict] = []

    async def event_generator():
        nonlocal collected_responses
        try:
            gen = handle_orchestrator_mode(
                db,
                orchestrator.id,
                data.conversation_id,
                data.content,
                selected_slave_ids if selected_slave_ids else None,
                iterations=data.iterations,
                broadcast_instructions=data.broadcast_instructions,
                orchestrator_instructions=data.orchestrator_instructions,
            )

            async for chunk in gen:
                # chunk is already "data: {...}\n\n"
                # Parse to collect for DB storage
                if chunk.startswith("data: "):
                    try:
                        payload = json.loads(chunk[6:].strip())
                        if not payload.get("done") and (payload.get("content") or "").strip():
                            collected_responses.append(payload)
                    except Exception:
                        pass
                yield chunk
        except Exception as exc:
            logger.exception("Chat stream failed for conversation %s", data.conversation_id)
            payload = json.dumps({"agent": "system", "content": f"Failed to process message: {exc}", "done": False})
            yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        finally:
            # After streaming, save assistant messages to DB when content exists.
            if collected_responses:
                await _save_assistant_messages(db, data.conversation_id, orchestrator.id, "orchestrator", collected_responses)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _save_assistant_messages(db, conversation_id: str, orchestrator_id: str, mode: str, responses: list[dict]):
    """Aggregate and save assistant messages."""
    orch_result = await db.execute(select(Agent).where(Agent.id == orchestrator_id))
    orch = orch_result.scalar_one_or_none()
    orch_id = orch.id if orch else None
    orch_name = orch.name if orch else "Orchestrator"

    grouped_messages: list[dict] = []
    for response in responses:
        agent_name = response.get("agent", "Unknown")
        content = response.get("content", "")
        message_type = response.get("message_type", "chat")
        group_key = response.get("group_key") or f"{message_type}:{agent_name}"
        if not grouped_messages or grouped_messages[-1]["group_key"] != group_key:
            grouped_messages.append({
                "group_key": group_key,
                "agent_name": agent_name,
                "message_type": message_type,
                "chunks": [content],
            })
        else:
            grouped_messages[-1]["chunks"].append(content)

    for grouped in grouped_messages:
        agent_name = grouped["agent_name"]
        full_content = "".join(grouped["chunks"]).strip()
        if not full_content:
            continue
        message_type = grouped["message_type"]
        is_orchestrator_message = (
            agent_name == orch_name
            or agent_name.startswith(f"{orch_name} ·")
            or agent_name.startswith(f"{orch_name} ->")
        )
        msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
            message_type=message_type,
            mode=mode,
            agent_id=orch_id if is_orchestrator_message else None,
            agent_name=agent_name if agent_name else orch_name,
        )
        db.add(msg)

    await db.commit()
