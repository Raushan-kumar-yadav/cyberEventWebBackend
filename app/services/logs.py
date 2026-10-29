import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import TeamLog, TeamPathEvent
from app.models.enums import PathEvent, QuestionEvent


def log_question(
    db: AsyncSession,
    team_id: int,
    event: QuestionEvent,
    question_id: uuid.UUID | None = None,
    **meta: Any,
) -> None:
    db.add(TeamLog(team_id=team_id, question_id=question_id, event=event, meta=meta))


def log_path(
    db: AsyncSession,
    team_id: int,
    path_id: int,
    event: PathEvent,
    at: datetime | None = None,
    question_id: uuid.UUID | None = None,
) -> None:
    db.add(
        TeamPathEvent(
            team_id=team_id,
            path_id=path_id,
            event=event,
            at=at or utcnow(),
            question_id=question_id,
        )
    )
