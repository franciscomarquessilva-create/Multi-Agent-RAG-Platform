import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from app.database import init_db, get_db
from app.config import get_settings
from app.routers import agents, conversations, chat, llm_logs, settings as settings_router
from app.routers import users as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directories exist
    settings = get_settings()
    os.makedirs("./data", exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    await init_db()
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


app = FastAPI(
    title="Multi-Agent RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Dev-User-Email",
                   "Cf-Access-Jwt-Assertion", "X-Impersonate-User-Id"],
)

app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(llm_logs.router)
app.include_router(settings_router.router)
app.include_router(users_router.router)


@app.get("/health")
async def health():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
    db_status = "ok"
    async for db in get_db():
        try:
            await db.execute(text("SELECT 1"))
        except Exception as exc:
            db_status = "error"
            import logging
            logging.getLogger(__name__).error("Health check DB error: %s", exc)
        break
    status = "ok" if db_status == "ok" else "degraded"
    return {"status": status, "db": db_status}
