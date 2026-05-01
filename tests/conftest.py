import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock

from fitness_bot.models import Base
from webapp.app import create_app
import webapp.api as api_module
import webapp.auth as auth_module

TRAINER_ID = 100
TRAINEE_ID = 200

TRAINER_H = {"X-Debug-User-Id": str(TRAINER_ID)}
TRAINEE_H = {"X-Debug-User-Id": str(TRAINEE_ID)}


@pytest_asyncio.fixture
async def app(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(api_module, "async_session", session_factory)
    monkeypatch.setattr(api_module, "TRAINER_ID", TRAINER_ID)
    monkeypatch.setattr(api_module, "TRAINEE_ID", TRAINEE_ID)
    monkeypatch.setattr(api_module, "_send_telegram", AsyncMock())
    monkeypatch.setattr(auth_module, "DEBUG", True)

    yield create_app()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
