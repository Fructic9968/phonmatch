"""Обработка квиза: переход между вопросами и сбор ответов."""

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update

from bot.handlers.results import send_results
from bot.keyboards.inline import QuizAnswerCallback, QuizTypeCallback, RestartCallback, quiz_answer_keyboard, quiz_type_keyboard
from bot.states.quiz import QuizState
from core.matching import find_matches
from core.quiz_config import QuizQuestion, get_questions_for_quiz
from db.database import get_session
from db.models import QuizSession, QuizType, User

router = Router()
logger = logging.getLogger(__name__)


def make_progress_bar(current: int, total: int) -> str:
    """Создать текстовый прогресс-бар."""
    return f"Вопрос {current} из {total}  [{'▓' * current}{'░' * (total - current)}]"


def _question_text(question: QuizQuestion, index: int, total: int) -> str:
    return f"{make_progress_bar(index + 1, total)}\n\n{question.text}"


async def _begin(callback: CallbackQuery, state: FSMContext, quiz_type: str) -> None:
    """Создать сеанс и показать первый вопрос."""
    if not isinstance(callback.message, Message):
        return
    questions = get_questions_for_quiz(quiz_type)
    try:
        async with get_session() as session:
            user_id = await session.scalar(select(User.id).where(User.telegram_id == callback.from_user.id))
            if user_id is None:
                await callback.message.answer("Сначала отправьте команду /start.")
                return
            quiz = QuizSession(user_id=user_id, quiz_type=QuizType(quiz_type), is_completed=False)
            session.add(quiz)
            await session.flush()
            session_id = quiz.id
            await session.commit()
    except Exception:
        logger.exception("Ошибка создания сеанса квиза")
        await callback.message.answer("Не удалось начать квиз. Попробуйте позже.")
        return
    await state.set_state(QuizState.answering)
    await state.set_data({"quiz_type": quiz_type, "session_id": session_id, "question_index": 0, "answers": {}, "message_id": callback.message.message_id})
    await callback.message.edit_text(_question_text(questions[0], 0, len(questions)), reply_markup=quiz_answer_keyboard(questions[0]))


@router.callback_query(QuizTypeCallback.filter())
async def choose_quiz(callback: CallbackQuery, callback_data: QuizTypeCallback, state: FSMContext) -> None:
    """Начать выбранный тип квиза."""
    await callback.answer()
    # Старая клавиатура выбора не должна прерывать действующий квиз.
    if await state.get_state() is not None:
        return
    await _begin(callback, state, callback_data.quiz_type.value)


@router.callback_query(RestartCallback.filter())
async def restart(callback: CallbackQuery, callback_data: RestartCallback, state: FSMContext) -> None:
    """Обработать выбор повторного прохождения или подтверждение прерывания."""
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    current_state = await state.get_state()
    data = await state.get_data()
    if current_state is not None and callback.message.message_id != data.get("interrupt_message_id"):
        return
    if callback_data.action == "continue":
        if current_state is not None:
            await state.update_data(interrupt_message_id=None)
            await callback.message.edit_text("Продолжайте отвечать на текущий вопрос выше.")
        return
    if callback_data.action == "types":
        await state.clear()
        await callback.message.edit_text("Выберите тип подбора:", reply_markup=quiz_type_keyboard())
    elif callback_data.action == "again":
        if current_state is not None:
            return
        if callback_data.quiz_type in ("quick", "normal", "precise"):
            await _begin(callback, state, callback_data.quiz_type)
        else:
            await callback.message.edit_text("Выберите тип подбора:", reply_markup=quiz_type_keyboard())


@router.callback_query(QuizAnswerCallback.filter())
async def answer_question(callback: CallbackQuery, callback_data: QuizAnswerCallback, state: FSMContext) -> None:
    """Проверить ответ, перейти к следующему вопросу или завершить квиз."""
    await callback.answer()
    if not isinstance(callback.message, Message) or await state.get_state() != QuizState.answering.state:
        return
    data = await state.get_data()
    if data.get("message_id") != callback.message.message_id:
        return
    questions = get_questions_for_quiz(data["quiz_type"])
    index = data["question_index"]
    if not 0 <= index < len(questions):
        return
    question = questions[index]
    if callback_data.question_key != question.key or callback_data.value not in {option.value for option in question.options}:
        return
    answers = {**data["answers"], question.key: callback_data.value}
    if index + 1 < len(questions):
        await state.update_data(answers=answers, question_index=index + 1)
        await callback.message.edit_text(_question_text(questions[index + 1], index + 1, len(questions)), reply_markup=quiz_answer_keyboard(questions[index + 1]))
        return
    await callback.message.edit_text("⏳ Подбираю смартфоны...")
    try:
        matches = await find_matches(answers, data["quiz_type"])
        async with get_session() as session:
            # Условное обновление защищает счётчик от повторного завершения.
            result = await session.execute(
                update(QuizSession).where(QuizSession.id == data["session_id"], QuizSession.is_completed.is_(False))
                .values(answers=answers, results=[asdict(match) for match in matches], is_completed=True, completed_at=datetime.now(timezone.utc))
                .returning(QuizSession.user_id)
            )
            user_id = result.scalar_one_or_none()
            if user_id is not None:
                await session.execute(update(User).where(User.id == user_id).values(total_quizzes=User.total_quizzes + 1))
            await session.commit()
        if user_id is None:
            await state.clear()
            await callback.message.edit_text("Этот квиз уже завершён. Начните новый подбор через /start.")
            return
    except Exception:
        logger.exception("Ошибка завершения квиза")
        # Состояние последнего вопроса сохраняется, чтобы ответ можно было отправить повторно.
        await callback.message.edit_text("Не удалось выполнить подбор. Попробуйте ещё раз.\n\n" + _question_text(question, index, len(questions)), reply_markup=quiz_answer_keyboard(question))
        return
    await state.clear()
    await send_results(callback.message, matches, answers, data["quiz_type"])
