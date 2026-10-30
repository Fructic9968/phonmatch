"""Модели каталога смартфонов, цен и сеансов квиза."""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей."""


class BudgetClass(str, Enum):
    """Ценовой сегмент смартфона."""

    BUDGET = "budget"
    LOWER_MID = "lower_mid"
    MID = "mid"
    UPPER_MID = "upper_mid"
    FLAGSHIP = "flagship"


class PurchaseChannel(str, Enum):
    """Канал покупки."""

    RETAILER = "retailer"
    MARKETPLACE = "marketplace"


class QuizType(str, Enum):
    """Длительность квиза."""

    QUICK = "quick"
    NORMAL = "normal"
    PRECISE = "precise"


class OS(str, Enum):
    """Операционная система смартфона."""

    ANDROID = "android"
    IOS = "ios"


def enum_type(enum: type[Enum], name: str) -> SAEnum:
    """Сохранять значения перечислений, а не имена элементов."""
    return SAEnum(enum, name=name, values_callable=lambda members: [member.value for member in members])


class Smartphone(Base):
    """Характеристики и оценки смартфона."""

    __tablename__ = "smartphones"
    __table_args__ = (UniqueConstraint("brand", "model", "storage_gb", name="uq_smartphones_brand_model_storage"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    budget_class: Mapped[BudgetClass] = mapped_column(enum_type(BudgetClass, "budgetclass"), index=True)
    os: Mapped[OS] = mapped_column(enum_type(OS, "os"))
    display_size: Mapped[float | None]
    display_refresh_rate: Mapped[int | None]
    processor: Mapped[str | None] = mapped_column(String)
    ram_gb: Mapped[int | None]
    storage_gb: Mapped[int | None]
    battery_mah: Mapped[int | None]
    camera_main_mp: Mapped[int | None]
    has_nfc: Mapped[bool] = mapped_column(Boolean, default=True)
    has_5g: Mapped[bool] = mapped_column(Boolean, default=False)
    has_wireless_charging: Mapped[bool] = mapped_column(Boolean, default=False)
    water_resistance: Mapped[str | None] = mapped_column(String)
    weight_g: Mapped[int | None]
    image_url: Mapped[str | None] = mapped_column(String)
    score_camera: Mapped[float | None]
    score_performance: Mapped[float | None]
    score_battery: Mapped[float | None]
    score_display: Mapped[float | None]
    score_overall: Mapped[float | None]
    source_id: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    prices: Mapped[list["SmartphonePrice"]] = relationship(back_populates="smartphone", cascade="all, delete-orphan")


class SmartphonePrice(Base):
    """Цена смартфона в конкретном магазине."""

    __tablename__ = "smartphone_prices"
    __table_args__ = (UniqueConstraint("smartphone_id", "store_name", name="uq_smartphone_prices_phone_store"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    smartphone_id: Mapped[int] = mapped_column(ForeignKey("smartphones.id"), index=True)
    channel: Mapped[PurchaseChannel] = mapped_column(enum_type(PurchaseChannel, "purchasechannel"), index=True)
    store_name: Mapped[str] = mapped_column(String)
    price: Mapped[int]
    url: Mapped[str | None] = mapped_column(String)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    smartphone: Mapped["Smartphone"] = relationship(back_populates="prices")


class User(Base):
    """Пользователь Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    language_code: Mapped[str | None] = mapped_column(String, default="ru")
    first_interaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_quizzes: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    quiz_sessions: Mapped[list["QuizSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class QuizSession(Base):
    """Ответы и результаты одного прохождения квиза."""

    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quiz_type: Mapped[QuizType] = mapped_column(enum_type(QuizType, "quiztype"))
    answers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped["User"] = relationship(back_populates="quiz_sessions")
