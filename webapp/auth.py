import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException

from fitness_bot.config import BOT_TOKEN, DEBUG
from fitness_bot.db import async_session
from fitness_bot.models import AuthToken

logger = logging.getLogger(__name__)


def _verify_init_data(init_data: str) -> int:
    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        logger.warning("Auth failed: missing hash. init_data preview: %.80s", init_data)
        raise HTTPException(401, detail="Missing hash in init data")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        logger.warning("Auth failed: HMAC mismatch. received=%s computed=%s", received_hash[:8], computed_hash[:8])
        raise HTTPException(401, detail="Invalid init data signature")

    user_data = json.loads(unquote(params.get("user", "{}")))
    user_id = user_data.get("id")
    if not user_id:
        logger.warning("Auth failed: no user id in init data")
        raise HTTPException(401, detail="No user in init data")

    return int(user_id)


async def _verify_auth_token(token: str) -> int:
    async with async_session() as db:
        auth_token = await db.get(AuthToken, token)
    if not auth_token:
        logger.warning("Auth failed: unknown token")
        raise HTTPException(401, detail="Invalid token")
    expires_at = auth_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        logger.warning("Auth failed: expired token")
        raise HTTPException(401, detail="Token expired")
    return auth_token.telegram_id


async def get_current_user(
    x_telegram_init_data: str = Header(default=""),
    x_auth_token: str = Header(default=""),
    x_debug_user_id: str = Header(default=""),
) -> int:
    if x_telegram_init_data:
        return _verify_init_data(x_telegram_init_data)
    if x_auth_token:
        return await _verify_auth_token(x_auth_token)
    if DEBUG and x_debug_user_id:
        return int(x_debug_user_id)
    logger.warning("Auth failed: no auth header (DEBUG=%s)", DEBUG)
    raise HTTPException(401, detail="Authentication required")
