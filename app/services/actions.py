from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import GameState, Team
from app.services import game_clock, progression, questions


# shared guard for every team game action
async def begin(db: AsyncSession, team: Team) -> tuple[GameState, Team, datetime]:
    game = await game_clock.require_running(db)
    team = await questions.lock_team(db, team)
    now = utcnow()
    if progression.frozen_until(team, now):
        raise HTTPException(status.HTTP_423_LOCKED, "Team is frozen while travelling")
    return game, team, now
