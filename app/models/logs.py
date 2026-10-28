import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.models.base import Base, JSONType, TimestampMixin
from app.models.enums import PathEvent, QuestionEvent, str_enum


class TeamLog(TimestampMixin, Base):
    __tablename__ = "team_logs"
    __table_args__ = (Index("ix_team_logs_team_created", "team_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    event: Mapped[QuestionEvent] = mapped_column(str_enum(QuestionEvent))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class TeamPathEvent(TimestampMixin, Base):
    __tablename__ = "team_path_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("paths.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    event: Mapped[PathEvent] = mapped_column(str_enum(PathEvent))
    at: Mapped[datetime] = mapped_column(default=utcnow)


class AdminAudit(TimestampMixin, Base):
    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
