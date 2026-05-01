import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock

from fitness_bot.models import Base, User
from webapp.app import create_app
import webapp.api as api_module
import webapp.auth as auth_module

TRAINER_ID = 100
TRAINEE_ID = 200

TRAINER_H = {"X-Debug-User-Id": str(TRAINER_ID)}
TRAINEE_H = {"X-Debug-User-Id": str(TRAINEE_ID)}

TEST_BOT_TOKEN = "1234567890:test_token"


def make_init_data(user_id: int, bot_token: str = TEST_BOT_TOKEN) -> str:
    user = json.dumps({"id": user_id, "first_name": "Test"})
    params = {"auth_date": str(int(time.time())), "user": user}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


@pytest_asyncio.fixture
async def app(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        db.add(User(telegram_id=TRAINER_ID, role="trainer", name="Test Trainer"))
        db.add(User(telegram_id=TRAINEE_ID, role="trainee", name="Test Trainee"))
        await db.commit()

    monkeypatch.setattr(api_module, "async_session", session_factory)
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


@pytest_asyncio.fixture
async def real_auth_session(monkeypatch):
    """In-memory DB + patches with DEBUG=False and real BOT_TOKEN. Yields the session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        db.add(User(telegram_id=TRAINER_ID, role="trainer", name="Test Trainer"))
        db.add(User(telegram_id=TRAINEE_ID, role="trainee", name="Test Trainee"))
        await db.commit()

    monkeypatch.setattr(api_module, "async_session", session_factory)
    monkeypatch.setattr(api_module, "_send_telegram", AsyncMock())
    monkeypatch.setattr(auth_module, "async_session", session_factory)
    monkeypatch.setattr(auth_module, "DEBUG", False)
    monkeypatch.setattr(auth_module, "BOT_TOKEN", TEST_BOT_TOKEN)

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def real_auth_client(real_auth_session):
    """HTTP client backed by the real_auth_session DB."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
