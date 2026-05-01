import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

import webapp.auth as auth_module
from webapp.auth import _verify_init_data

TEST_TOKEN = "1234567890:test_token"


def _make_init_data(user_id: int, bot_token: str = TEST_TOKEN) -> str:
    user = json.dumps({"id": user_id, "first_name": "Test"})
    params = {"auth_date": str(int(time.time())), "user": user}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def test_valid_init_data(monkeypatch):
    monkeypatch.setattr(auth_module, "BOT_TOKEN", TEST_TOKEN)
    assert _verify_init_data(_make_init_data(12345)) == 12345


def test_wrong_token_rejected(monkeypatch):
    monkeypatch.setattr(auth_module, "BOT_TOKEN", TEST_TOKEN)
    init_data = _make_init_data(12345, bot_token="wrong_token")
    with pytest.raises(HTTPException) as exc:
        _verify_init_data(init_data)
    assert exc.value.status_code == 401


def test_missing_hash_rejected(monkeypatch):
    monkeypatch.setattr(auth_module, "BOT_TOKEN", TEST_TOKEN)
    params = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 1})}
    with pytest.raises(HTTPException) as exc:
        _verify_init_data(urlencode(params))
    assert exc.value.status_code == 401


def test_no_user_rejected(monkeypatch):
    monkeypatch.setattr(auth_module, "BOT_TOKEN", TEST_TOKEN)
    params = {"auth_date": str(int(time.time()))}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", TEST_TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(HTTPException) as exc:
        _verify_init_data(urlencode(params))
    assert exc.value.status_code == 401
