"""Приветствие, регистрация пользователя и выбор квиза."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.dialects.postgresql import insert

from bot.keyboards.inline import QuizTypeCallback, quiz_type_keyboard
from db.database import get_session
from db.models import User

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    """Зарегистрировать нового пользователя и предложить выбор квиза."""
    if message.from_user is None:
        return
    user = message.from_user
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
    await message.answer(
        "👋 Привет! Я PhonMatch — помогу подобрать идеальный смартфон!\n\n"
        "Выбери тип подбора:\n\n"
        "⚡ Быстрый (4 вопроса) — за 30 секунд\n"
        "📋 Обычный (8 вопросов) — за 2 минуты\n"
        "🎯 Точный (14 вопросов) — за 5 минут",
        reply_markup=quiz_type_keyboard(),
    )


@router.callback_query(QuizTypeCallback.filter())
async def choose_quiz(callback: CallbackQuery, callback_data: QuizTypeCallback) -> None:
    """Подтвердить нажатие до реализации квиза."""
    await callback.answer("🚧 Квиз в разработке!", show_alert=True)
