"""Минимальное REST API проекта."""

from fastapi import FastAPI

app = FastAPI(title="PhonMatch API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Проверить доступность сервиса."""
    return {"status": "ok", "service": "PhonMatch"}
