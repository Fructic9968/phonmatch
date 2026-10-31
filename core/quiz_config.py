"""Конфигурация вопросов квиза для всех типов подбора."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QuizOption:
    """Вариант ответа."""
    text: str
    value: str


@dataclass(frozen=True)
class QuizQuestion:
    """Вопрос и его варианты."""
    key: str
    text: str
    options: list[QuizOption]


def _question(key: str, text: str, options: list[tuple[str, str]]) -> QuizQuestion:
    return QuizQuestion(key, text, [QuizOption(*option) for option in options])


QUESTIONS = {q.key: q for q in [
    _question("budget", "💰 Какой у вас бюджет на смартфон?", [("До 15 000 ₽", "budget"), ("15 000 – 25 000 ₽", "lower_mid"), ("25 000 – 40 000 ₽", "mid"), ("40 000 – 60 000 ₽", "upper_mid"), ("60 000 ₽ и выше", "flagship")]),
    _question("priority", "🎯 Для чего вам в основном нужен смартфон?", [("📱 Звонки и мессенджеры", "basic"), ("📸 Соцсети и фото", "camera"), ("🎮 Игры и видео", "gaming"), ("💼 Работа и мультизадачность", "productivity"), ("🔄 Всего понемногу", "balanced")]),
    _question("purchase_channel", "🏬 Где планируете покупать?", [("🏪 Ритейлер (DNS, М.Видео, МТС...)", "retailer"), ("📦 Маркетплейс (Ozon, WB, Я.Маркет)", "marketplace"), ("🤷 Не определился — покажите оба", "both")]),
    _question("brand_preference", "📱 Есть предпочтения по бренду?", [("Samsung", "samsung"), ("Apple", "apple"), ("Xiaomi", "xiaomi"), ("Honor", "honor"), ("Другой", "other"), ("Нет, любой", "any")]),
    _question("screen_size", '📐 Какой размер экрана предпочитаете?', [('📱 Компактный (до 6.2")', "compact"), ('📱 Средний (6.2" – 6.5")', "medium"), ('📱 Большой (6.5" и больше)', "large"), ("🤷 Неважно", "any")]),
    _question("camera_importance", "📸 Насколько важна камера?", [("1 — Совсем неважна", "1"), ("2 — Не особо", "2"), ("3 — Средне", "3"), ("4 — Важна", "4"), ("5 — Очень важна!", "5")]),
    _question("battery_importance", "🔋 Насколько важна автономность (батарея)?", [("1 — Всегда рядом розетка", "1"), ("2 — Не особо важна", "2"), ("3 — Средне", "3"), ("4 — Важна", "4"), ("5 — Критически важна!", "5")]),
    _question("gaming", "🎮 Играете в требовательные мобильные игры?", [("🎮 Да, часто (Genshin, PUBG...)", "heavy"), ("🕹️ Иногда, казуально", "casual"), ("❌ Нет, не играю", "no")]),
    _question("storage", "💾 Сколько встроенной памяти нужно?", [("64 ГБ — хватит", "64"), ("128 ГБ — стандарт", "128"), ("256 ГБ — с запасом", "256"), ("512+ ГБ — максимум", "512")]),
    _question("needs_5g", "📶 Нужна поддержка 5G?", [("✅ Да, обязательно", "yes"), ("🤷 Желательно, но не критично", "preferred"), ("❌ Не нужна", "no")]),
    _question("needs_nfc", "💳 Нужен NFC (бесконтактная оплата)?", [("✅ Да, обязательно", "yes"), ("❌ Не нужен", "no")]),
    _question("refresh_rate", "🔄 Частота обновления экрана?", [("60 Гц — достаточно", "60"), ("90-120 Гц — хочу плавность", "high"), ("🤷 Не знаю что это", "any")]),
    _question("water_resistance", "💧 Важна ли защита от воды?", [("✅ Да, обязательно", "yes"), ("🤷 Желательно", "preferred"), ("❌ Неважно", "no")]),
    _question("wireless_charging", "🔌 Нужна беспроводная зарядка?", [("✅ Да", "yes"), ("❌ Не нужна", "no")]),
]}

QUIZ_QUESTIONS_MAP: dict[str, list[str]] = {
    "quick": ["budget", "priority", "purchase_channel", "brand_preference"],
    "normal": ["budget", "priority", "purchase_channel", "brand_preference", "screen_size", "camera_importance", "battery_importance", "gaming"],
    "precise": ["budget", "priority", "purchase_channel", "brand_preference", "screen_size", "camera_importance", "battery_importance", "gaming", "storage", "needs_5g", "needs_nfc", "refresh_rate", "water_resistance", "wireless_charging"],
}


def get_questions_for_quiz(quiz_type: str) -> list[QuizQuestion]:
    """Вернуть вопросы выбранного типа; неизвестный тип вызывает KeyError."""
    return [QUESTIONS[key] for key in QUIZ_QUESTIONS_MAP[quiz_type]]
