import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set SECRET_KEY before any app imports so get_settings() caches the correct value
os.environ.setdefault("SECRET_KEY", "dGVzdC1zZWNyZXQta2V5LWZvci11bml0LXRlc3Rpbmc=")

from app.config import get_settings
get_settings.cache_clear()

from app.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(autouse=True)
async def reset_sse_app_status():
    """Reset sse_starlette AppStatus event to the current event loop before each test.

    sse_starlette initialises AppStatus.should_exit_event at import time, binding it
    to the event loop that exists when the module is first loaded. pytest-asyncio
    creates a fresh event loop per test function, which causes RuntimeError when the
    SSE response tries to await the stale event. Re-creating the Event here ensures
    it is always bound to the active loop.
    """
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = asyncio.Event()
    yield


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
