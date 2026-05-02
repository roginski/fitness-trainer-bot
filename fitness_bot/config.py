import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
TRAINER_ID: int | None = int(os.environ["TRAINER_ID"]) if os.environ.get("TRAINER_ID") else None
TRAINEE_ID: int | None = int(os.environ["TRAINEE_ID"]) if os.environ.get("TRAINEE_ID") else None
def _fix_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

DATABASE_URL: str = _fix_db_url(os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///fitness.db"))
WEBAPP_URL: str = os.environ.get("WEBAPP_URL", "")
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
