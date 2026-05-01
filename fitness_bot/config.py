import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
TRAINER_ID: int | None = int(os.environ["TRAINER_ID"]) if os.environ.get("TRAINER_ID") else None
TRAINEE_ID: int | None = int(os.environ["TRAINEE_ID"]) if os.environ.get("TRAINEE_ID") else None
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///fitness.db")
WEBAPP_URL: str = os.environ.get("WEBAPP_URL", "")
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
