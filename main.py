import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from fitness_bot.config import BOT_TOKEN
from fitness_bot.db import init_db
from fitness_bot.handlers import router

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


async def main() -> None:
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.error()
    async def error_handler(event: ErrorEvent) -> None:
        logging.exception("Unhandled exception", exc_info=event.exception)

    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
