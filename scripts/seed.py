"""CLI для управления данными смартфонов."""

import argparse
import asyncio
import sys
from pathlib import Path

# При запуске файла напрямую Python добавляет в sys.path только scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import engine  # noqa: E402
from services.seeder import clear_smartphones, print_stats, seed_smartphones  # noqa: E402


async def run() -> None:
    """Разобрать команду и закрыть соединения после её выполнения."""
    parser = argparse.ArgumentParser(description="Управление каталогом смартфонов")
    subparsers = parser.add_subparsers(dest="command", required=True)
    load = subparsers.add_parser("load", help="Загрузить каталог")
    load.add_argument("--update", action="store_true", help="Обновить существующие записи и заменить их цены")
    load.add_argument("--file", default="data/smartphones_seed.json", help="Путь к JSON-каталогу")
    subparsers.add_parser("clear", help="Удалить все смартфоны и цены")
    subparsers.add_parser("stats", help="Показать статистику")
    args = parser.parse_args()
    try:
        if args.command == "load":
            await seed_smartphones(args.file, update=args.update)
        elif args.command == "clear":
            await clear_smartphones()
        else:
            await print_stats()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
