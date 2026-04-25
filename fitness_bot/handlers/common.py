from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, MenuButtonWebApp, Message, WebAppInfo

from ..config import TRAINER_ID, TRAINEE_ID, WEBAPP_URL

router = Router()


async def _set_menu_button(bot: Bot, chat_id: int, url: str, label: str) -> None:
    if not WEBAPP_URL:
        return
    await bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonWebApp(text=label, web_app=WebAppInfo(url=url)),
    )


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot) -> None:
    uid = message.from_user.id
    if uid == TRAINER_ID:
        await _set_menu_button(bot, uid, f"{WEBAPP_URL}/trainer", "Workout Builder")
        await message.answer(
            "Hello, trainer!\n\n"
            "Tap <b>Workout Builder</b> below to create a workout.\n"
            "/report — get the latest completed workout report"
        )
    elif uid == TRAINEE_ID:
        await _set_menu_button(bot, uid, f"{WEBAPP_URL}/trainee", "My Workout")
        await message.answer(
            "Hello!\n\n"
            "Tap <b>My Workout</b> below to log your workout."
        )
    else:
        await message.answer("You are not authorized to use this bot.")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Nothing to cancel.")
        return
    await state.clear()
    await message.answer("Cancelled.")
