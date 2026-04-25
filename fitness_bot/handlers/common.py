from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..config import TRAINER_ID, TRAINEE_ID

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id
    if uid == TRAINER_ID:
        await message.answer(
            "Hello, trainer!\n\n"
            "/new_workout — create a new workout\n"
            "/report — get the latest completed workout report"
        )
    elif uid == TRAINEE_ID:
        await message.answer(
            "Hello!\n\n"
            "/workout — view and log your current workout"
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
