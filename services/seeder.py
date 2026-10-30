"""Импорт смартфонов из JSON-файла в базу данных."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from db.database import get_session
from db.models import BudgetClass, OS, PurchaseChannel, Smartphone, SmartphonePrice


async def seed_smartphones(json_path: str = "data/smartphones_seed.json", update: bool = False) -> None:
    """Загрузить каталог, изолируя транзакцию каждого смартфона."""
    print(f"📱 Загрузка смартфонов из {json_path}...")
    with Path(json_path).open(encoding="utf-8") as file:
        records: list[dict[str, Any]] = json.load(file)
    added = skipped = errors = updated = 0
    for record in records:
        name = f"{record.get('brand', '?')} {record.get('model', '?')}"
        try:
            async with get_session() as session:
                phone = await session.scalar(
                    select(Smartphone).where(Smartphone.slug == record["slug"])
                    .options(selectinload(Smartphone.prices))
                )
                if phone is not None and not update:
                    skipped += 1
                    print(f"⏭️ {name} ({record.get('budget_class')}) — уже существует, пропущен")
                    continue
                existed = phone is not None
                attributes = {key: value for key, value in record.items() if key != "prices"}
                attributes["budget_class"] = BudgetClass(attributes["budget_class"])
                attributes["os"] = OS(attributes["os"])
                prices = [SmartphonePrice(**{**price, "channel": PurchaseChannel(price["channel"])}) for price in record["prices"]]
                if phone is None:
                    phone = Smartphone(**attributes, prices=prices)
                    session.add(phone)
                else:
                    for key, value in attributes.items():
                        setattr(phone, key, value)
                    # Сначала удаляем старые цены, чтобы не нарушить уникальность магазина.
                    phone.prices.clear()
                    await session.flush()
                    phone.prices.extend(prices)
                await session.commit()
                if existed:
                    updated += 1
                    action = "обновлён"
                else:
                    added += 1
                    action = "добавлен"
                print(f"✅ {name} ({record.get('budget_class')}) — {action}")
        except Exception as exc:
            errors += 1
            print(f"❌ Ошибка при загрузке {name}: {exc}")
    print(f"\n📊 Итого:\n   Добавлено: {added}\n   Обновлено: {updated}\n   Пропущено: {skipped}\n   Ошибок: {errors}")


async def clear_smartphones() -> None:
    """Удалить все цены и смартфоны."""
    async with get_session() as session:
        await session.execute(delete(SmartphonePrice))
        result = await session.execute(delete(Smartphone))
        await session.commit()
    print(f"🗑️ Удалено смартфонов: {result.rowcount}")


async def print_stats() -> None:
    """Вывести количество смартфонов по классам и общее количество цен."""
    async with get_session() as session:
        rows = await session.execute(select(Smartphone.budget_class, func.count()).group_by(Smartphone.budget_class))
        counts = dict(rows.all())
        prices = await session.scalar(select(func.count()).select_from(SmartphonePrice))
    icons = ("💰", "💰💰", "💰💰💰", "💳", "👑")
    print("📈 Статистика по классам:")
    for icon, budget in zip(icons, BudgetClass):
        print(f"   {icon} {budget.value}: {counts.get(budget, 0)} смартфонов")
    print(f"   🏷️ Цен: {prices}")
