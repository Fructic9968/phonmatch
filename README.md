# PhonMatch

Telegram-бот для подбора смартфонов по ответам на квиз. Сейчас реализованы приветствие и регистрация, а квиз и подбор находятся в разработке. REST API содержит проверку доступности.

## Запуск

Нужны Python 3.11+ и запущенный PostgreSQL с созданной базой `phonmatch`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Укажите BOT_TOKEN от BotFather и параметры PostgreSQL в .env
alembic revision --autogenerate -m "initial"
alembic upgrade head
python -m bot.main
```

Первая команда Alembic создаёт файл миграции: проверьте его перед применением и сохраните в репозитории. Выполняйте миграции до первого запуска бота: бот создаёт отсутствующие таблицы при старте, но `create_all` не заменяет миграции и не обновляет существующую схему. Настройки, включая `BOT_TOKEN`, нужны и для Alembic.

Запуск заготовки API: `uvicorn api.main:app --host 0.0.0.0 --port 8000`. Проверка: `GET /health`. Настройки `API_HOST` и `API_PORT` зарезервированы для будущего программного запуска API; параметры команды uvicorn задаются отдельно.
