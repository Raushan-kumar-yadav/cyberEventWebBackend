import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Path(Base):
    __tablename__ = "paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    start_region: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(default=0)


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    story: Mapped[str] = mapped_column(Text)
    monument: Mapped[str] = mapped_column(String(128))
    hint1: Mapped[str | None] = mapped_column(Text)
    hint2: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(255))
    flag: Mapped[str] = mapped_column(String(256))
    case_sensitive: Mapped[bool] = mapped_column(default=True)
    is_final: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)

    base_points: Mapped[int]
    min_points: Mapped[int] = mapped_column(default=0)
    decay_interval_seconds: Mapped[int] = mapped_column(default=0)
    decay_points: Mapped[int] = mapped_column(default=0)
    retries: Mapped[int] = mapped_column(default=3)
    block_seconds: Mapped[int] = mapped_column(default=300)

    unlocked_at: Mapped[datetime | None]
    unlocked_game_seconds: Mapped[int | None]
    unlocked_by_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )
    first_solved_at: Mapped[datetime | None]
    first_solved_by_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )
    blocked_until: Mapped[datetime | None]
    blocked_by_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )


class PathQuestion(Base):
    __tablename__ = "path_questions"
    __table_args__ = (UniqueConstraint("path_id", "question_id"),)

    path_id: Mapped[int] = mapped_column(
        ForeignKey("paths.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
