"""Настройки приложения из переменных окружения и файла .env."""

from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Параметры бота, базы данных и API."""

    BOT_TOKEN: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "phonmatch"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        """Вернуть URL для асинхронного подключения к PostgreSQL."""
        user = quote(self.DB_USER, safe="")
        password = quote(self.DB_PASSWORD, safe="")
        database = quote(self.DB_NAME, safe="")
        return f"postgresql+asyncpg://{user}:{password}@{self.DB_HOST}:{self.DB_PORT}/{database}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
