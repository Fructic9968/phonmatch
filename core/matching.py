"""Движок подбора смартфонов по ответам пользователя."""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from db.database import get_session
from db.models import BudgetClass, PurchaseChannel, Smartphone

logger = logging.getLogger(__name__)

PRIORITY_WEIGHTS: dict[str, dict[str, float]] = {
    "basic": {"camera": 1.0, "performance": 1.0, "battery": 1.5, "display": 1.0},
    "camera": {"camera": 3.0, "performance": 1.0, "battery": 1.0, "display": 1.5},
    "gaming": {"camera": 0.5, "performance": 3.0, "battery": 1.5, "display": 2.0},
    "productivity": {"camera": 1.0, "performance": 2.5, "battery": 1.5, "display": 1.5},
    "balanced": {"camera": 1.5, "performance": 1.5, "battery": 1.5, "display": 1.5},
}


@dataclass
class MatchResult:
    """Результат подбора смартфона и лучшие доступные цены."""
    smartphone_id: int
    score: float
    reasons: list[str]
    price_info: dict[str, dict[str, Any]]


def get_weights(answers: dict[str, Any]) -> dict[str, float]:
    """Скорректировать веса по приоритету и детальным ответам."""
    weights = PRIORITY_WEIGHTS.get(answers.get("priority"), PRIORITY_WEIGHTS["balanced"]).copy()
    for key in ("camera", "battery"):
        if f"{key}_importance" in answers:
            weights[key] *= int(answers[f"{key}_importance"]) / 3
    if answers.get("gaming") == "heavy":
        weights["performance"] *= 1.5
    elif answers.get("gaming") == "no":
        weights["performance"] *= 0.7
    return weights


def calculate_score(phone: Smartphone, weights: dict[str, float], answers: dict[str, Any]) -> float:
    """Рассчитать балл с учётом предпочтений; неизвестные оценки считаются нейтральными (5)."""
    base = sum((getattr(phone, f"score_{key}") if getattr(phone, f"score_{key}") is not None else 5.0) * weight for key, weight in weights.items()) / sum(weights.values()) * 10
    bonus = 0
    size = phone.display_size
    preference = answers.get("screen_size")
    # Границы не пересекаются: компактный < 6.2, средний [6.2, 6.5), большой >= 6.5.
    if size is not None and ((preference == "compact" and size < 6.2) or (preference == "medium" and 6.2 <= size < 6.5) or (preference == "large" and size >= 6.5)):
        bonus += 3
    if answers.get("storage") and phone.storage_gb is not None and phone.storage_gb >= int(answers["storage"]):
        bonus += 3
    rate = phone.display_refresh_rate
    if rate is not None and ((answers.get("refresh_rate") == "high" and rate >= 90) or (answers.get("refresh_rate") == "60" and rate >= 60)):
        bonus += 2
    if answers.get("water_resistance") in ("yes", "preferred"):
        bonus += 3 if phone.water_resistance else -3
    if answers.get("wireless_charging") == "yes" and phone.has_wireless_charging:
        bonus += 3
    if answers.get("needs_5g") == "preferred" and not phone.has_5g:
        bonus -= 3
    return round(max(0.0, min(100.0, base + bonus)), 1)


def generate_reasons(phone: Smartphone, weights: dict[str, float], answers: dict[str, Any]) -> list[str]:
    """Выбрать до трёх релевантных причин, не выдумывая характеристики."""
    candidates: list[tuple[float, str]] = []
    if phone.score_camera is not None and phone.score_camera >= 8:
        detail = f" ({phone.camera_main_mp} Мп)" if phone.camera_main_mp is not None else ""
        candidates.append((weights['camera'] * phone.score_camera, f"Отличная камера{detail}"))
    if phone.score_performance is not None and phone.score_performance >= 8:
        detail = f" ({phone.processor})" if phone.processor else ""
        candidates.append((weights['performance'] * phone.score_performance, f"Мощный процессор{detail}"))
    if phone.score_battery is not None and phone.score_battery >= 8:
        detail = f" ({phone.battery_mah} мАч)" if phone.battery_mah is not None else ""
        candidates.append((weights['battery'] * phone.score_battery, f"Хорошая автономность{detail}"))
    if phone.score_display is not None and phone.score_display >= 8:
        parts = []
        if phone.display_size is not None:
            parts.append(f'{phone.display_size}″')
        if phone.display_refresh_rate is not None:
            parts.append(f'{phone.display_refresh_rate} Гц')
        detail = f" ({', '.join(parts)})" if parts else ""
        candidates.append((weights['display'] * phone.score_display, f"Качественный дисплей{detail}"))
    if phone.has_nfc:
        candidates.append((15 if answers.get('needs_nfc') == 'yes' else 3, "Есть NFC"))
    if phone.water_resistance:
        candidates.append((15 if answers.get('water_resistance') in ('yes', 'preferred') else 3, f"Защита от воды и пыли {phone.water_resistance}"))
    if phone.has_wireless_charging:
        candidates.append((15 if answers.get('wireless_charging') == 'yes' else 3, "Беспроводная зарядка"))
    if phone.has_5g and answers.get('needs_5g') in ('yes', 'preferred'):
        candidates.append((15, "Поддержка 5G"))
    # Для недорогих моделей оценки могут быть ниже 8: добавляем факты,
    # а не называем характеристики отличными без оснований.
    if len(candidates) < 3:
        if phone.camera_main_mp is not None and not any("камера" in text.lower() for _, text in candidates):
            candidates.append((weights["camera"], f"Основная камера {phone.camera_main_mp} Мп"))
        if phone.processor and not any("процессор" in text.lower() for _, text in candidates):
            candidates.append((weights["performance"], f"Процессор {phone.processor}"))
        if phone.battery_mah is not None and not any("автономность" in text.lower() for _, text in candidates):
            candidates.append((weights["battery"], f"Батарея {phone.battery_mah} мАч"))
    return [text for _, text in sorted(candidates, key=lambda x: -x[0])[:3]]


def _prices(phone: Smartphone, channel: str) -> dict[str, dict[str, Any]]:
    """Выбрать минимальную цену в наличии для каждого запрошенного канала."""
    result: dict[str, dict[str, Any]] = {}
    for price in phone.prices:
        key = price.channel.value if isinstance(price.channel, PurchaseChannel) else price.channel
        if not price.in_stock or (channel != "both" and channel != key):
            continue
        if key not in result or price.price < result[key]["price"]:
            result[key] = {"store_name": price.store_name, "price": price.price, "url": price.url}
    return result


async def find_matches(answers: dict[str, Any], quiz_type: str, limit: int | None = None) -> list[MatchResult]:
    """Отфильтровать и ранжировать активные смартфоны с загруженными ценами."""
    if quiz_type not in ("quick", "normal", "precise"):
        raise ValueError(f"Неизвестный тип квиза: {quiz_type}")
    budget = BudgetClass(answers["budget"])
    stmt = select(Smartphone).where(Smartphone.budget_class == budget, Smartphone.is_active.is_(True)).options(selectinload(Smartphone.prices))
    brand = answers.get("brand_preference", "any")
    if brand not in ("any", "other"):
        stmt = stmt.where(func.lower(Smartphone.brand) == brand.lower())
    if answers.get("needs_nfc") == "yes":
        stmt = stmt.where(Smartphone.has_nfc.is_(True))
    if answers.get("needs_5g") == "yes":
        stmt = stmt.where(Smartphone.has_5g.is_(True))
    try:
        async with get_session() as session:
            phones = (await session.scalars(stmt)).all()
            weights = get_weights(answers)
            matches = [MatchResult(phone.id, calculate_score(phone, weights, answers), generate_reasons(phone, weights, answers), _prices(phone, answers.get("purchase_channel", "both"))) for phone in phones]
    except Exception:
        logger.exception("Ошибка поиска смартфонов")
        raise
    matches.sort(key=lambda result: (-result.score, result.smartphone_id))
    return matches[:max(0, limit if limit is not None else (3 if quiz_type == "quick" else 5))]
