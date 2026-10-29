import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PointLedger, Team
from app.models.enums import LedgerReason


# caller must hold the team row lock
def apply(
    db: AsyncSession,
    team: Team,
    delta: int,
    reason: LedgerReason,
    question_id: uuid.UUID | None = None,
    admin_id: int | None = None,
    note: str | None = None,
) -> None:
    balance = team.points + delta
    if balance < 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Not enough points")
    team.points = balance
    db.add(
        PointLedger(
            team_id=team.id,
            delta=delta,
            balance_after=balance,
            reason=reason,
            question_id=question_id,
            admin_id=admin_id,
            note=note,
        )
    )
