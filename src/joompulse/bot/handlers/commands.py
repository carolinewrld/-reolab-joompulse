from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "JoomPulse Creative Intelligence.\n"
        "Доступно: /status, /digest, /creative <id>."
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer("ok")
