import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_log import LLMLog


async def create_llm_log(
    db: AsyncSession,
    *,
    agent_id: str | None,
    agent_name: str,
    model: str,
    request_payload: dict,
    response_payload: dict | None = None,
    error: str | None = None,
) -> LLMLog:
    log = LLMLog(
        agent_id=agent_id,
        agent_name=agent_name,
        model=model,
        request_payload=json.dumps(request_payload),
        response_payload=json.dumps(response_payload) if response_payload is not None else None,
        error=error,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_llm_logs(db: AsyncSession, *, limit: int = 200) -> list[LLMLog]:
    result = await db.execute(select(LLMLog).order_by(LLMLog.created_at.desc()).limit(limit))
    return result.scalars().all()
