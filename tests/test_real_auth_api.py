"""
Integration tests that send real auth headers through the full HTTP stack.
These catch bugs in the auth path that debug-header tests miss.
"""
from datetime import datetime, timedelta, timezone

from fitness_bot.models import AuthToken
from fitness_bot.db import async_session
from tests.conftest import TRAINER_ID, TRAINEE_ID, make_init_data


def _h(user_id: int, wrong_token: bool = False) -> dict:
    token = "bad_token" if wrong_token else None
    kwargs = {"bot_token": token} if token else {}
    return {"X-Telegram-Init-Data": make_init_data(user_id, **kwargs)}


async def test_trainer_authenticated_via_init_data(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers=_h(TRAINER_ID))
    assert r.status_code == 200


async def test_trainee_authenticated_via_init_data(real_auth_client):
    r = await real_auth_client.get("/api/workout/current", headers=_h(TRAINEE_ID))
    assert r.status_code == 200


async def test_invalid_signature_rejected(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers=_h(TRAINER_ID, wrong_token=True))
    assert r.status_code == 401


async def test_malformed_init_data_rejected(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Telegram-Init-Data": "not=valid&data=here"})
    assert r.status_code == 401


async def test_no_header_rejected_when_debug_off(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft")
    assert r.status_code == 401


async def test_debug_header_rejected_when_debug_off(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Debug-User-Id": str(TRAINER_ID)})
    assert r.status_code == 401


async def test_trainee_init_data_cannot_access_trainer_endpoint(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers=_h(TRAINEE_ID))
    assert r.status_code == 403


async def test_trainer_init_data_cannot_access_trainee_endpoint(real_auth_client):
    r = await real_auth_client.get("/api/workout/current", headers=_h(TRAINER_ID))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Token auth
# ---------------------------------------------------------------------------

async def _make_token(user_id: int, session_factory, hours: int = 24) -> str:
    token = "testtoken_" + str(user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    async with session_factory() as db:
        db.add(AuthToken(token=token, telegram_id=user_id, expires_at=expires_at))
        await db.commit()
    return token


async def test_trainer_authenticated_via_token(real_auth_client, real_auth_session):
    token = await _make_token(TRAINER_ID, real_auth_session)
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Auth-Token": token})
    assert r.status_code == 200


async def test_trainee_authenticated_via_token(real_auth_client, real_auth_session):
    token = await _make_token(TRAINEE_ID, real_auth_session)
    r = await real_auth_client.get("/api/workout/current", headers={"X-Auth-Token": token})
    assert r.status_code == 200


async def test_expired_token_rejected(real_auth_client, real_auth_session):
    token = await _make_token(TRAINER_ID, real_auth_session, hours=-1)
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Auth-Token": token})
    assert r.status_code == 401


async def test_unknown_token_rejected(real_auth_client):
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Auth-Token": "nosuchtoken"})
    assert r.status_code == 401


async def test_token_role_enforcement(real_auth_client, real_auth_session):
    token = await _make_token(TRAINEE_ID, real_auth_session)
    r = await real_auth_client.get("/api/workout/draft", headers={"X-Auth-Token": token})
    assert r.status_code == 403
