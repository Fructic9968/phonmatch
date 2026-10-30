"""Inline-клавиатура выбора типа квиза."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import QuizType


class QuizTypeCallback(CallbackData, prefix="quiz"):
    """Данные кнопки выбора квиза."""

    quiz_type: QuizType


def quiz_type_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с тремя вариантами квиза."""
    builder = InlineKeyboardBuilder()
    for label, quiz_type in (("⚡ Быстрый", QuizType.QUICK), ("📋 Обычный", QuizType.NORMAL), ("🎯 Точный", QuizType.PRECISE)):
        builder.button(text=label, callback_data=QuizTypeCallback(quiz_type=quiz_type))
    builder.adjust(1)
    return builder.as_markup()


# TODO: Добавить клавиатуры вопросов и результатов квиза.
