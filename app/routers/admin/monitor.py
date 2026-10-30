import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB, CurrentAdmin
from app.models import FinalLeaderboard
from app.models.enums import GameStatus, QuestionEvent
from app.schemas.monitor import (
    AdminMapOut,
    AuditOut,
    FinalLeaderboardOut,
    LeaderboardRow,
    MapQuestion,
    TeamDetailOut,
    TeamLogOut,
    TeamSummary,
)
from app.services import audit, content, game_clock, leaderboard, monitor

router = APIRouter()

Limit = Annotated[int, Query(ge=1, le=1000)]


@router.get("/leaderboard")
async def live_leaderboard(admin: CurrentAdmin, db: DB) -> list[LeaderboardRow]:
    return await leaderboard.ranking(db)


@router.get("/map")
async def admin_map(admin: CurrentAdmin, db: DB) -> AdminMapOut:
    return await monitor.admin_map(db)


@router.get("/team/details")
async def team_details(admin: CurrentAdmin, db: DB) -> list[TeamSummary]:
    return await monitor.team_summaries(db)


@router.get("/team/{team_id}")
async def team_detail(team_id: int, admin: CurrentAdmin, db: DB) -> TeamDetailOut:
    return await monitor.team_detail(db, team_id)


@router.get("/logs")
async def team_logs(
    admin: CurrentAdmin,
    db: DB,
    team_id: int | None = None,
    question_id: uuid.UUID | None = None,
    event: QuestionEvent | None = None,
    limit: Limit = 200,
) -> list[TeamLogOut]:
    return await monitor.team_logs(db, team_id, question_id, event, limit)


@router.get("/audit")
async def audit_trail(
    admin: CurrentAdmin, db: DB, action: str | None = None, limit: Limit = 200
) -> list[AuditOut]:
    return await monitor.audit_trail(db, action, limit)


@router.get("/blocks")
async def blocks(admin: CurrentAdmin, db: DB) -> list[MapQuestion]:
    return await monitor.map_questions(db, blocked_only=True)


@router.post("/question/{question_id}/unblock")
async def unblock(question_id: uuid.UUID, admin: CurrentAdmin, db: DB) -> MapQuestion:
    question = await content.get_question(db, question_id, lock=True)
    if not (question.blocked_until and question.blocked_until > utcnow()):
        raise HTTPException(status.HTTP_409_CONFLICT, "Question is not blocked")
    cleared = await monitor.unblock(db, question)
    audit.record(db, admin.id, "question_unblock", question.code, waits_cleared=cleared)
    await db.commit()
    return next(q for q in await monitor.map_questions(db) if q.question_id == question_id)


@router.post("/create/final_leaderboard", status_code=status.HTTP_201_CREATED)
async def create_final_leaderboard(admin: CurrentAdmin, db: DB) -> FinalLeaderboardOut:
    game = await game_clock.get_game(db)
    if game_clock.effective_status(game, utcnow()) != GameStatus.ENDED:
        raise HTTPException(status.HTTP_409_CONFLICT, "End the game first")
    rows = await leaderboard.ranking(db)
    snapshot = FinalLeaderboard(admin_id=admin.id, rows=[r.model_dump(mode="json") for r in rows])
    db.add(snapshot)
    await db.flush()
    audit.record(db, admin.id, "final_leaderboard", str(snapshot.id), teams=len(rows))
    await db.commit()
    return FinalLeaderboardOut(id=snapshot.id, created_at=snapshot.created_at, rows=rows)


@router.get("/final_leaderboard")
async def final_leaderboard(admin: CurrentAdmin, db: DB) -> FinalLeaderboardOut:
    snapshot = await db.scalar(
        select(FinalLeaderboard).order_by(FinalLeaderboard.id.desc()).limit(1)
    )
    if snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No final leaderboard yet")
    return FinalLeaderboardOut(
        id=snapshot.id,
        created_at=snapshot.created_at,
        rows=[LeaderboardRow.model_validate(row) for row in snapshot.rows],
    )
