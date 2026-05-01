from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo
from sqlalchemy import func, select

from ..config import WEBAPP_URL
from ..db import async_session
from ..models import User

router = Router()


async def _set_menu_button(bot: Bot, chat_id: int, url: str, label: str) -> None:
    if not WEBAPP_URL:
        return
    await bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonWebApp(text=label, web_app=WebAppInfo(url=url)),
    )


async def _welcome(message: Message, bot: Bot, user: User) -> None:
    if user.role == "trainer":
        await _set_menu_button(bot, user.telegram_id, f"{WEBAPP_URL}/trainer", "Workout Builder")
        await message.answer(
            f"Hello, {user.name}!\n\n"
            "Tap <b>Workout Builder</b> below to create a workout.\n"
            "/report — get the latest completed workout report"
        )
    else:
        await _set_menu_button(bot, user.telegram_id, f"{WEBAPP_URL}/trainee", "My Workout")
        await message.answer(
            f"Hello, {user.name}!\n\n"
            "Tap <b>My Workout</b> below to log your workout."
        )


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot) -> None:
    async with async_session() as db:
        user = await db.get(User, message.from_user.id)

    if user:
        await _welcome(message, bot, user)
    else:
        await message.answer("Welcome! Use /register to get started.")


@router.message(Command("register"))
async def cmd_register(message: Message, bot: Bot) -> None:
    async with async_session() as db:
        existing = await db.get(User, message.from_user.id)
        if existing:
            await message.answer(f"You are already registered as {existing.role}.")
            return

        trainer_count = await db.scalar(select(func.count()).where(User.role == "trainer"))
        trainee_count = await db.scalar(select(func.count()).where(User.role == "trainee"))

        if trainer_count == 0:
            role = "trainer"
        elif trainee_count == 0:
            role = "trainee"
        else:
            await message.answer("Registration is full.")
            return

        name = message.from_user.first_name or str(message.from_user.id)
        user = User(telegram_id=message.from_user.id, role=role, name=name)
        db.add(user)
        await db.commit()

    await message.answer(f"Registered as {role}!")
    await _welcome(message, bot, user)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Nothing to cancel.")
        return
    await state.clear()
    await message.answer("Cancelled.")
