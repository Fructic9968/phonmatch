"""Тесты квиза и подбора без Telegram и действующей базы."""

import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("BOT_TOKEN", "123456:ABC")

from aiogram.types import CallbackQuery, Message
from sqlalchemy.dialects import postgresql

from bot.handlers.quiz import answer_question, make_progress_bar
from bot.handlers.results import format_phone_card
from bot.keyboards.inline import QuizAnswerCallback, quiz_answer_keyboard
from bot.states.quiz import QuizState
from core.matching import MatchResult, _prices, calculate_score, find_matches, generate_reasons, get_weights
from core.quiz_config import QUIZ_QUESTIONS_MAP, get_questions_for_quiz
from db.models import PurchaseChannel, Smartphone, SmartphonePrice


def phone(**overrides: object) -> Smartphone:
    """Создать объект каталога для теста."""
    attrs = dict(id=1, brand="<Brand>", model="Test & Phone", score_camera=9.0,
                 score_performance=8.0, score_battery=8.0, score_display=8.0,
                 camera_main_mp=50, processor="Chip", battery_mah=5000,
                 display_size=6.5, display_refresh_rate=120, ram_gb=8, storage_gb=256,
                 has_nfc=True, has_5g=True, has_wireless_charging=False, water_resistance="IP68")
    attrs.update(overrides)
    return Smartphone(**attrs)


class QuizConfigTests(unittest.TestCase):
    """Конфигурация и callback-данные."""

    def test_lengths_and_callbacks(self) -> None:
        for kind, count in (("quick", 4), ("normal", 8), ("precise", 14)):
            questions = get_questions_for_quiz(kind)
            self.assertEqual(len(questions), count)
            self.assertEqual([q.key for q in questions], QUIZ_QUESTIONS_MAP[kind])
            for question in questions:
                for row in quiz_answer_keyboard(question).inline_keyboard:
                    for button in row:
                        self.assertLessEqual(len(button.callback_data.encode()), 64)
                        decoded = QuizAnswerCallback.unpack(button.callback_data)
                        self.assertEqual(decoded.question_key, question.key)
                        self.assertIn(decoded.value, [o.value for o in question.options])
        self.assertEqual(make_progress_bar(3, 8), "Вопрос 3 из 8  [▓▓▓░░░░░]")


class ScoringTests(unittest.TestCase):
    """Оценка, цены и форматирование."""

    def test_weights_and_bonuses(self) -> None:
        weights = get_weights(dict(priority="camera", camera_importance="5", battery_importance="1", gaming="heavy"))
        self.assertEqual(weights["camera"], 5)
        self.assertAlmostEqual(weights["battery"], 1 / 3)
        self.assertEqual(weights["performance"], 1.5)
        device = phone()
        base = calculate_score(device, weights, {})
        enriched = calculate_score(device, weights, {"screen_size": "large", "storage": "256", "refresh_rate": "high", "water_resistance": "yes"})
        self.assertGreater(enriched, base)
        self.assertLessEqual(enriched, 100)
        self.assertTrue(any("камера" in text for text in generate_reasons(device, weights, {})))

    def test_missing_scores_and_price_filter(self) -> None:
        device = phone(score_camera=None, score_battery=None, has_5g=False)
        score = calculate_score(device, get_weights({}), {"needs_5g": "preferred"})
        self.assertTrue(0 <= score <= 100)
        device.prices = [SmartphonePrice(channel=PurchaseChannel.RETAILER, store_name="A", price=100, in_stock=True),
                         SmartphonePrice(channel=PurchaseChannel.RETAILER, store_name="B", price=80, in_stock=False),
                         SmartphonePrice(channel=PurchaseChannel.MARKETPLACE, store_name="C", price=90, in_stock=True)]
        self.assertEqual(_prices(device, "both")["retailer"]["price"], 100)
        self.assertEqual(set(_prices(device, "marketplace")), {"marketplace"})

    def test_html_escaped_and_prices(self) -> None:
        match = MatchResult(1, 85.2, ["<reason>"], {"retailer": {"store_name": "D&N", "price": 100000}, "marketplace": {"store_name": "Ozon", "price": 90000}})
        card = format_phone_card(1, phone(), match, "both")
        self.assertIn("&lt;Brand&gt;", card)
        self.assertIn("&lt;reason&gt;", card)
        self.assertIn("10 000 ₽", card)
        self.assertNotIn("Ozon", format_phone_card(1, phone(), match, "retailer"))


class AsyncFlowTests(unittest.IsolatedAsyncioTestCase):
    """Пустая база и корректное завершение FSM."""

    async def test_empty_database_and_filters(self) -> None:
        session = MagicMock()
        session.scalars = AsyncMock(return_value=MagicMock(all=lambda: []))
        @asynccontextmanager
        async def get_session():
            yield session
        with patch("core.matching.get_session", get_session):
            results = await find_matches({"budget": "mid", "brand_preference": "samsung", "needs_nfc": "yes", "needs_5g": "yes"}, "quick")
        self.assertEqual(results, [])
        sql = str(session.scalars.await_args.args[0].compile(dialect=postgresql.dialect()))
        for field in ("budget_class", "lower(", "has_nfc", "has_5g", "is_active"):
            self.assertIn(field, sql)

    async def test_finish_resets_fsm_and_saves(self) -> None:
        message = MagicMock(spec=Message)
        message.message_id = 7
        message.edit_text = AsyncMock()
        callback = MagicMock(spec=CallbackQuery)
        callback.message = message
        callback.answer = AsyncMock()
        state = MagicMock()
        state.get_state = AsyncMock(return_value=QuizState.answering.state)
        state.get_data = AsyncMock(return_value={"quiz_type": "quick", "session_id": 2, "question_index": 3, "message_id": 7, "answers": {"budget": "mid", "priority": "camera", "purchase_channel": "both"}})
        state.clear = AsyncMock()
        session = MagicMock()
        session.execute = AsyncMock(side_effect=[SimpleNamespace(scalar_one_or_none=lambda: 3), None])
        session.commit = AsyncMock()
        @asynccontextmanager
        async def get_session():
            yield session
        with patch("bot.handlers.quiz.get_session", get_session), patch("bot.handlers.quiz.find_matches", AsyncMock(return_value=[])), patch("bot.handlers.quiz.send_results", AsyncMock()) as send:
            await answer_question(callback, QuizAnswerCallback(question_key="brand_preference", value="any"), state)
        state.clear.assert_awaited_once()
        session.commit.assert_awaited_once()
        send.assert_awaited_once()
        self.assertEqual(send.await_args.args[2]["brand_preference"], "any")

    async def test_stale_callback_ignored(self) -> None:
        message = MagicMock(spec=Message)
        message.message_id = 7
        message.edit_text = AsyncMock()
        callback = MagicMock(spec=CallbackQuery)
        callback.message = message
        callback.answer = AsyncMock()
        state = MagicMock()
        state.get_state = AsyncMock(return_value=QuizState.answering.state)
        state.get_data = AsyncMock(return_value={"quiz_type": "quick", "question_index": 1, "message_id": 7, "answers": {}})
        await answer_question(callback, QuizAnswerCallback(question_key="budget", value="mid"), state)
        callback.answer.assert_awaited_once()
        message.edit_text.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
