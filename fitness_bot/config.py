import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
TRAINER_ID: int = int(os.environ["TRAINER_ID"])
TRAINEE_ID: int = int(os.environ["TRAINEE_ID"])
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///fitness.db")
