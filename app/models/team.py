from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (CheckConstraint("points >= 0", name="points_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(255))
    session_version: Mapped[int] = mapped_column(default=0)

    points: Mapped[int] = mapped_column(default=0)
    powerups_used: Mapped[int] = mapped_column(default=0)
    playthroughs: Mapped[int] = mapped_column(default=0)
    has_reached_delhi: Mapped[bool] = mapped_column(default=False)
    reached_delhi_at: Mapped[datetime | None]

    current_path_id: Mapped[int | None] = mapped_column(
        ForeignKey("paths.id", ondelete="SET NULL")
    )
    switch_from_path_id: Mapped[int | None] = mapped_column(
        ForeignKey("paths.id", ondelete="SET NULL")
    )
    frozen_until: Mapped[datetime | None]
