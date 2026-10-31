"""Отображение результатов подбора смартфонов."""

import logging
from html import escape
from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.keyboards.inline import restart_keyboard
from core.matching import MatchResult
from db.database import get_session
from db.models import Smartphone

router = Router()
logger = logging.getLogger(__name__)


def format_phone_card(rank: int, phone: Smartphone, match: MatchResult, purchase_channel: str) -> str:
    """Сформировать безопасную HTML-карточку с известными характеристиками."""
    lines = [f"🏆 <b>#{rank} {escape(phone.brand)} {escape(phone.model)}</b>", f"⭐ Совпадение: {match.score:g}%", ""]
    screen = []
    if phone.display_size is not None:
        screen.append(f'{phone.display_size}″')
    if phone.display_refresh_rate is not None:
        screen.append(f'{phone.display_refresh_rate} Гц')
    if screen:
        lines.append(f"📱 Экран: {' / '.join(screen)}")
    if phone.processor:
        lines.append(f"⚡ Процессор: {escape(phone.processor)}")
    if phone.camera_main_mp is not None:
        lines.append(f"📸 Камера: {phone.camera_main_mp} Мп")
    if phone.battery_mah is not None:
        lines.append(f"🔋 Батарея: {phone.battery_mah} мАч")
    if phone.ram_gb is not None or phone.storage_gb is not None:
        memory = "/".join(str(v) for v in (phone.ram_gb, phone.storage_gb) if v is not None)
        lines.append(f"💾 Память: {memory} ГБ")
    features = ([escape(phone.water_resistance)] if phone.water_resistance else []) + (["NFC"] if phone.has_nfc else []) + (["5G"] if phone.has_5g else [])
    if features:
        lines.append("🛡️ " + " • ".join(features))
    lines.extend(["", "💰 <b>Цена:</b>"])
    shown = []
    for channel, icon in (("retailer", "🏪"), ("marketplace", "📦")):
        price = match.price_info.get(channel)
        if price and purchase_channel in (channel, "both"):
            shown.append(price)
            lines.append(f"{icon} {escape(str(price['store_name']))}: {price['price']:,} ₽".replace(",", " "))
    if not shown:
        lines.append("Нет доступных цен")
    if purchase_channel == "both" and len(shown) == 2:
        saving = shown[0]["price"] - shown[1]["price"]
        if saving > 0:
            lines.append(f"💡 Экономия на маркетплейсе: {saving:,} ₽".replace(",", " "))
    if match.reasons:
        lines.append("")
        lines.extend(f"✅ {escape(reason)}" for reason in match.reasons[:3])
    return "\n".join(lines)


async def send_results(message_or_callback: Message | CallbackQuery, results: list[MatchResult], answers: dict[str, Any], quiz_type: str) -> None:
    """Отправить результаты в чат и предложить повторить квиз."""
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback
    if not isinstance(message, Message):
        return
    if not results:
        await message.answer("К сожалению, по вашим критериям ничего не нашлось. Попробуйте смягчить требования.", reply_markup=restart_keyboard(quiz_type))
        return
    try:
        async with get_session() as session:
            phones = (await session.scalars(select(Smartphone).where(Smartphone.id.in_([r.smartphone_id for r in results])))).all()
            by_id = {phone.id: phone for phone in phones}
    except Exception:
        logger.exception("Ошибка загрузки карточек смартфонов")
        await message.answer("Не удалось загрузить карточки. Попробуйте пройти квиз снова.", reply_markup=restart_keyboard(quiz_type))
        return
    await message.answer("🎉 Готово! Вот ваш персональный подбор:")
    for rank, match in enumerate(results, 1):
        phone = by_id.get(match.smartphone_id)
        if phone:
            await message.answer(format_phone_card(rank, phone, match, answers.get("purchase_channel", "both")), parse_mode="HTML")
    await message.answer("Хотите попробовать ещё раз?", reply_markup=restart_keyboard(quiz_type))
