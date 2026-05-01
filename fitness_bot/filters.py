from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from .db import async_session
from .models import User


class RoleFilter(BaseFilter):
    def __init__(self, role: str) -> None:
        self.role = role

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        async with async_session() as db:
            user = await db.get(User, event.from_user.id)
        return user is not None and user.role == self.role
