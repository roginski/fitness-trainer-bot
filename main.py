import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from alembic import command
from alembic.config import Config

from fitness_bot.config import BOT_TOKEN, TRAINER_ID, TRAINEE_ID
from fitness_bot.db import async_session
from fitness_bot.handlers import router
from fitness_bot.models import User
from webapp.app import create_app

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


async def seed_dev_users() -> None:
    """Seed trainer/trainee from .env if set and not already in DB."""
    seeds = []
    if TRAINER_ID:
        seeds.append((TRAINER_ID, "trainer", "Dev Trainer"))
    if TRAINEE_ID:
        seeds.append((TRAINEE_ID, "trainee", "Dev Trainee"))

    if not seeds:
        return

    async with async_session() as db:
        for telegram_id, role, name in seeds:
            existing = await db.get(User, telegram_id)
            if not existing:
                db.add(User(telegram_id=telegram_id, role=role, name=name))
        await db.commit()


async def run_bot() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.error()
    async def error_handler(event: ErrorEvent) -> None:
        logging.exception("Unhandled exception", exc_info=event.exception)

    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def main() -> None:
    await seed_dev_users()

    config = uvicorn.Config(create_app(), host="0.0.0.0", port=8000, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # aiogram owns SIGINT/SIGTERM

    bot_task = asyncio.create_task(run_bot())
    web_task = asyncio.create_task(server.serve())

    done, pending = await asyncio.wait([bot_task, web_task], return_when=asyncio.FIRST_COMPLETED)
    server.should_exit = True
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    run_migrations()
    asyncio.run(main())
