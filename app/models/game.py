from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.models.base import Base, JSONType, TimestampMixin
from app.models.enums import GameStatus, str_enum


class GameState(Base):
    __tablename__ = "game_state"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    status: Mapped[GameStatus] = mapped_column(
        str_enum(GameStatus), default=GameStatus.NOT_STARTED
    )
    start_at: Mapped[datetime | None]
    end_at: Mapped[datetime | None]
    paused_at: Mapped[datetime | None]
    paused_seconds: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=0)


class StorePrice(Base):
    __tablename__ = "store_prices"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class PriceChange(TimestampMixin, Base):
    __tablename__ = "price_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32))
    old_value: Mapped[int]
    new_value: Mapped[int]
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))


class FinalLeaderboard(TimestampMixin, Base):
    __tablename__ = "final_leaderboards"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONType)
