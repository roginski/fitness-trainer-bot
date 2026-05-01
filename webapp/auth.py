import hashlib
import hmac
import json
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException

from fitness_bot.config import BOT_TOKEN, DEBUG


def _verify_init_data(init_data: str) -> int:
    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, detail="Missing hash in init data")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(401, detail="Invalid init data signature")

    user_data = json.loads(unquote(params.get("user", "{}")))
    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(401, detail="No user in init data")

    return int(user_id)


async def get_current_user(
    x_telegram_init_data: str = Header(default=""),
    x_debug_user_id: str = Header(default=""),
) -> int:
    if x_telegram_init_data:
        return _verify_init_data(x_telegram_init_data)
    if DEBUG and x_debug_user_id:
        return int(x_debug_user_id)
    raise HTTPException(401, detail="Authentication required")
