"""Точка входа Telegram-бота."""

import asyncio

from aiogram import Bot, Dispatcher

from bot.handlers.start import router
from config import Settings
from db.database import engine, init_db


async def main() -> None:
    """Инициализировать базу и запустить polling."""
    settings = Settings()
    bot = Bot(token=settings.BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    try:
        await init_db()
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
