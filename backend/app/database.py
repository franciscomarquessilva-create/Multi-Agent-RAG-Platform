import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings
import logging


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    db_url = settings.database_url
    # Ensure directory exists for SQLite
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    return create_async_engine(db_url, echo=False)


engine = get_engine()
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight SQLite migrations for existing local deployments.
        settings = get_settings()
        if settings.database_url.startswith("sqlite"):
            table_cols = {}
            for table in ("agents", "conversations", "messages"):
                result = await conn.execute(text(f"PRAGMA table_info({table})"))
                table_cols[table] = {row[1] for row in result.fetchall()}

            if "agent_type" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN agent_type VARCHAR(20) NOT NULL DEFAULT 'slave'"))
            if "purpose" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN purpose TEXT NOT NULL DEFAULT ''"))
            if "instructions" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN instructions TEXT NOT NULL DEFAULT ''"))
            if "orchestrator_mode" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN orchestrator_mode VARCHAR(20) NOT NULL DEFAULT 'orchestrate'"))
            if "allowed_slave_ids_json" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN allowed_slave_ids_json TEXT NOT NULL DEFAULT '[]'"))
            if "orchestration_rules_json" not in table_cols["agents"]:
                await conn.execute(text("ALTER TABLE agents ADD COLUMN orchestration_rules_json TEXT NOT NULL DEFAULT '[]'"))

            # Backfill agent_type from legacy is_orchestrator flag.
            await conn.execute(text("UPDATE agents SET agent_type='orchestrator' WHERE is_orchestrator = 1"))
            await conn.execute(text("UPDATE agents SET agent_type='slave' WHERE is_orchestrator = 0"))

            if "orchestrator_id" not in table_cols["conversations"]:
                await conn.execute(text("ALTER TABLE conversations ADD COLUMN orchestrator_id VARCHAR(36)"))
                # Best effort backfill: assign current orchestrator to existing conversations.
                orch_result = await conn.execute(text("SELECT id FROM agents WHERE agent_type='orchestrator' OR is_orchestrator = 1 ORDER BY created_at LIMIT 1"))
                row = orch_result.first()
                if row:
                    await conn.execute(text("UPDATE conversations SET orchestrator_id = :oid WHERE orchestrator_id IS NULL"), {"oid": row[0]})

            if "message_type" not in table_cols["messages"]:
                await conn.execute(text("ALTER TABLE messages ADD COLUMN message_type VARCHAR(20) NOT NULL DEFAULT 'chat'"))

            # Integrity repair for old data: conversations can still have NULL/orphan orchestrator IDs.
            fallback_result = await conn.execute(
                text("SELECT id FROM agents WHERE agent_type='orchestrator' OR is_orchestrator = 1 ORDER BY created_at LIMIT 1")
            )
            fallback = fallback_result.first()
            if fallback:
                fallback_id = fallback[0]
                null_fix = await conn.execute(
                    text("UPDATE conversations SET orchestrator_id = :oid WHERE orchestrator_id IS NULL"),
                    {"oid": fallback_id},
                )
                orphan_fix = await conn.execute(
                    text(
                        """
                        UPDATE conversations
                        SET orchestrator_id = :oid
                        WHERE orchestrator_id IS NOT NULL
                          AND orchestrator_id NOT IN (SELECT id FROM agents)
                        """
                    ),
                    {"oid": fallback_id},
                )
                if null_fix.rowcount or orphan_fix.rowcount:
                    logger.warning(
                        "Repaired conversation orchestrator links (null=%s, orphan=%s)",
                        null_fix.rowcount or 0,
                        orphan_fix.rowcount or 0,
                    )
