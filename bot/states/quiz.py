"""FSM-состояния квиза."""

from aiogram.fsm.state import State, StatesGroup


class QuizState(StatesGroup):
    """Единственное состояние прохождения квиза."""
    answering = State()
