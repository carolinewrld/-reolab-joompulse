from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from joompulse.bot.handlers import commands
from joompulse.config import get_settings
from joompulse.logging import configure_logging, get_logger


async def run() -> None:
    configure_logging()
    log = get_logger(__name__)
    settings = get_settings()

    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        log.warning("bot.disabled", reason="no_token")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(commands.router)

    log.info("bot.start")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
