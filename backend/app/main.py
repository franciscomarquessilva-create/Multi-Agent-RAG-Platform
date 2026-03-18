import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
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


app = FastAPI(
    title="Multi-Agent RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(llm_logs.router)
app.include_router(settings_router.router)
app.include_router(users_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
