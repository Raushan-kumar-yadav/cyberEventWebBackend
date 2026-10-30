from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.security import hash_password
from app.models import Team
from app.models.enums import LedgerReason
from app.schemas.admin import TeamCreate, TeamUpdate
from app.services import points, progression


async def get_team(db: AsyncSession, team_id: int, lock: bool = False) -> Team:
    team = await db.get(Team, team_id, with_for_update=lock, populate_existing=lock)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return team


async def create_team(db: AsyncSession, data: TeamCreate) -> Team:
    if await db.scalar(select(Team.id).where(Team.username == data.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    team = Team(username=data.username, name=data.name, password_hash=hash_password(data.password))
    db.add(team)
    await db.flush()
    return team


def update_team(team: Team, data: TeamUpdate) -> list[str]:
    changed = []
    if data.name is not None:
        team.name = data.name
        changed.append("name")
    if data.password is not None:
        team.password_hash = hash_password(data.password)
        team.session_version += 1
        changed.append("password")
    return changed


def adjust_points(db: AsyncSession, team: Team, delta: int, reason: str, admin_id: int) -> None:
    if delta == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "delta cannot be 0")
    points.apply(db, team, delta, LedgerReason.ADMIN_ADJUST, admin_id=admin_id, note=reason)


def unfreeze(team: Team) -> None:
    if progression.frozen_until(team, utcnow()) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Team is not frozen")
    # switch completes early, team stays on the new path
    team.frozen_until = None
    team.switch_from_path_id = None
