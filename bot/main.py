"""Точка входа Telegram-бота."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation

from bot.handlers.start import router as start_router
from bot.handlers.quiz import router as quiz_router
from bot.handlers.results import router as results_router
from config import Settings
from db.database import engine, init_db


async def main() -> None:
    """Инициализировать базу и запустить polling."""
    settings = Settings()
    bot = Bot(token=settings.BOT_TOKEN)
    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    dispatcher.include_router(start_router)
    dispatcher.include_router(quiz_router)
    dispatcher.include_router(results_router)
    try:
        await init_db()
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
