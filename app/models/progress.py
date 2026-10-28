import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import QuestionStatus, str_enum


class TeamQuestionState(Base):
    __tablename__ = "team_question_states"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[QuestionStatus] = mapped_column(
        str_enum(QuestionStatus), default=QuestionStatus.ACTIVE
    )
    attempts_used: Mapped[int] = mapped_column(default=0)
    extra_retries: Mapped[int] = mapped_column(default=0)
    hint1_owned: Mapped[bool] = mapped_column(default=False)
    hint2_owned: Mapped[bool] = mapped_column(default=False)
    points_awarded: Mapped[int] = mapped_column(default=0)
    viewed_at: Mapped[datetime | None]
    wait_until: Mapped[datetime | None]
    solved_at: Mapped[datetime | None]
