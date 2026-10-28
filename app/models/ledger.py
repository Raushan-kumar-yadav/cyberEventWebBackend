import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import LedgerReason, str_enum


class PointLedger(TimestampMixin, Base):
    __tablename__ = "point_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    delta: Mapped[int]
    balance_after: Mapped[int]
    reason: Mapped[LedgerReason] = mapped_column(str_enum(LedgerReason))
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(255))
