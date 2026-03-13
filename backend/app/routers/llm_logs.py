from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.llm_log import LLMLogResponse
from app.services.llm_log_service import list_llm_logs


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/llm", response_model=list[LLMLogResponse])
async def list_llm_logs_endpoint(
    limit: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    return await list_llm_logs(db, limit=limit)
