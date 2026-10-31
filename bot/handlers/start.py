"""Приветствие, регистрация пользователя и выбор квиза."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.dialects.postgresql import insert

from bot.keyboards.inline import interrupt_keyboard, quiz_type_keyboard
from db.database import get_session
from db.models import User

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    """Зарегистрировать пользователя и предложить выбор квиза."""
    if message.from_user is None:
        return
    user = message.from_user
    try:
        async with get_session() as session:
            statement = insert(User).values(
                telegram_id=user.id, username=user.username, first_name=user.first_name,
                language_code=user.language_code or "ru",
            ).on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={"username": user.username, "first_name": user.first_name},
            )
            await session.execute(statement)
            await session.commit()
    except Exception:
        logger.exception("Ошибка регистрации пользователя")
        await message.answer("Не удалось подключиться к базе данных. Попробуйте позже.")
        return
    if await state.get_state() is not None:
        prompt = await message.answer("Прервать текущий квиз?", reply_markup=interrupt_keyboard())
        await state.update_data(interrupt_message_id=prompt.message_id)
        return
    await state.clear()
    await message.answer(
        "👋 Привет! Я PhonMatch — помогу подобрать идеальный смартфон!\n\n"
        "Выбери тип подбора:\n\n"
        "⚡ Быстрый (4 вопроса) — за 30 секунд\n"
        "📋 Обычный (8 вопросов) — за 2 минуты\n"
        "🎯 Точный (14 вопросов) — за 5 минут",
        reply_markup=quiz_type_keyboard(),
    )
