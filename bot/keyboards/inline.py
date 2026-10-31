"""Inline-клавиатура выбора типа квиза."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import QuizType
from core.quiz_config import QuizQuestion


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





class QuizAnswerCallback(CallbackData, prefix="qa"):
    """Ответ на вопрос квиза."""
    question_key: str
    value: str


class RestartCallback(CallbackData, prefix="restart"):
    """Повторить квиз, выбрать другой тип или продолжить текущий."""
    action: str
    quiz_type: str = "none"


def quiz_answer_keyboard(question: "QuizQuestion") -> InlineKeyboardMarkup:
    """Создать клавиатуру вариантов ответа."""
    builder = InlineKeyboardBuilder()
    for option in question.options:
        builder.button(text=option.text, callback_data=QuizAnswerCallback(question_key=question.key, value=option.value))
    builder.adjust(2 if len(question.options) <= 3 and all(len(o.text) <= 22 for o in question.options) else 1)
    return builder.as_markup()


def restart_keyboard(quiz_type: str = "none") -> InlineKeyboardMarkup:
    """Предложить повторить текущий квиз или выбрать другой."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data=RestartCallback(action="again", quiz_type=quiz_type))
    builder.button(text="📋 Другой тип квиза", callback_data=RestartCallback(action="types"))
    builder.adjust(1)
    return builder.as_markup()


def interrupt_keyboard() -> InlineKeyboardMarkup:
    """Запросить подтверждение прерывания текущего квиза."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, прервать", callback_data=RestartCallback(action="types"))
    builder.button(text="Нет, продолжить", callback_data=RestartCallback(action="continue"))
    builder.adjust(1)
    return builder.as_markup()
