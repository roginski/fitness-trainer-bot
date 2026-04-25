import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from fitness_bot.config import BOT_TOKEN
from fitness_bot.db import init_db
from fitness_bot.handlers import router
from webapp.app import create_app

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


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
    await init_db()

    config = uvicorn.Config(create_app(), host="0.0.0.0", port=8000, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # aiogram owns SIGINT/SIGTERM

    bot_task = asyncio.create_task(run_bot())
    web_task = asyncio.create_task(server.serve())

    # When the bot stops (Ctrl+C), shut down the web server too
    done, pending = await asyncio.wait([bot_task, web_task], return_when=asyncio.FIRST_COMPLETED)
    server.should_exit = True
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
