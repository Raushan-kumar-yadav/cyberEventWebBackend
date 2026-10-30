from fastapi import APIRouter, status

from app.deps import DB, CurrentAdmin
from app.schemas.admin import PointsAdjust, TeamCreate, TeamUpdate
from app.schemas.monitor import TeamSummary
from app.services import audit, monitor, teams

router = APIRouter()


async def _summary(db: DB, team_id: int) -> TeamSummary:
    return (await monitor.team_summaries(db, team_id))[0]


@router.post("/team", status_code=status.HTTP_201_CREATED)
async def create_team(body: TeamCreate, admin: CurrentAdmin, db: DB) -> TeamSummary:
    team = await teams.create_team(db, body)
    audit.record(db, admin.id, "team_create", body.username, name=body.name)
    await db.commit()
    return await _summary(db, team.id)


@router.patch("/team/{team_id}")
async def update_team(team_id: int, body: TeamUpdate, admin: CurrentAdmin, db: DB) -> TeamSummary:
    team = await teams.get_team(db, team_id, lock=True)
    changed = teams.update_team(team, body)
    # field names only, never the password
    audit.record(db, admin.id, "team_update", team.username, fields=changed)
    await db.commit()
    return await _summary(db, team_id)


@router.post("/team/{team_id}/points")
async def adjust_points(
    team_id: int, body: PointsAdjust, admin: CurrentAdmin, db: DB
) -> TeamSummary:
    team = await teams.get_team(db, team_id, lock=True)
    teams.adjust_points(db, team, body.delta, body.reason, admin.id)
    audit.record(db, admin.id, "points_adjust", team.username, delta=body.delta, reason=body.reason)
    await db.commit()
    return await _summary(db, team_id)


@router.post("/team/{team_id}/unfreeze")
async def unfreeze(team_id: int, admin: CurrentAdmin, db: DB) -> TeamSummary:
    team = await teams.get_team(db, team_id, lock=True)
    teams.unfreeze(team)
    audit.record(db, admin.id, "team_unfreeze", team.username)
    await db.commit()
    return await _summary(db, team_id)


@router.post("/team/{team_id}/logout", status_code=status.HTTP_204_NO_CONTENT)
async def force_logout(team_id: int, admin: CurrentAdmin, db: DB) -> None:
    team = await teams.get_team(db, team_id, lock=True)
    team.session_version += 1
    audit.record(db, admin.id, "team_logout", team.username)
    await db.commit()
