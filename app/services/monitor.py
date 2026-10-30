import uuid
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import AdminAudit, PointLedger, Question, Team, TeamLog, TeamPathEvent
from app.models import TeamQuestionState as State
from app.models.enums import QuestionEvent
from app.schemas.monitor import (
    AdminMapOut,
    AuditOut,
    LedgerOut,
    MapQuestion,
    PathEventOut,
    TeamDetailOut,
    TeamLogOut,
    TeamSummary,
)
from app.services import game_clock, progression, scoring


async def team_summaries(db: AsyncSession, team_id: int | None = None) -> list[TeamSummary]:
    now = utcnow()
    stmt = select(Team).order_by(Team.id)
    done_stmt = select(State.team_id, State.question_id).where(State.status.in_(progression.DONE))
    if team_id is not None:
        stmt = stmt.where(Team.id == team_id)
        done_stmt = done_stmt.where(State.team_id == team_id)

    by_path = await progression.enabled_questions_by_path(db)
    done: dict[int, set[uuid.UUID]] = defaultdict(set)
    for tid, qid in await db.execute(done_stmt):
        done[tid].add(qid)

    summaries = []
    for team in await db.scalars(stmt):
        path = team.current_path_id
        current = progression.next_question(by_path.get(path, []), done[team.id]) if path else None
        summaries.append(
            TeamSummary(
                team_id=team.id,
                team_name=team.name,
                username=team.username,
                points=team.points,
                current_path_id=path,
                current_question_id=current,
                frozen_until=progression.frozen_until(team, now),
                has_reached_delhi=team.has_reached_delhi,
                playthroughs=team.playthroughs,
                powerups_used=team.powerups_used,
            )
        )
    return summaries


async def map_questions(db: AsyncSession, blocked_only: bool = False) -> list[MapQuestion]:
    now = utcnow()
    active = game_clock.active_seconds(await game_clock.get_game(db), now)
    stmt = select(Question).order_by(Question.code)
    if blocked_only:
        stmt = stmt.where(Question.blocked_until > now)
    return [
        MapQuestion(
            question_id=q.id,
            code=q.code,
            title=q.title,
            enabled=q.enabled,
            base_points=q.base_points,
            current_points=scoring.current_points(q, active),
            unlocked_at=q.unlocked_at,
            unlocked_by_team_id=q.unlocked_by_team_id,
            seconds_since_unlock=scoring.seconds_since_unlock(q, active),
            next_drop_in_seconds=scoring.next_drop_in(q, active),
            first_solved_by_team_id=q.first_solved_by_team_id,
            blocked_until=q.blocked_until if q.blocked_until and q.blocked_until > now else None,
            blocked_by_team_id=q.blocked_by_team_id,
        )
        for q in await db.scalars(stmt)
    ]


async def admin_map(db: AsyncSession) -> AdminMapOut:
    return AdminMapOut(teams=await team_summaries(db), questions=await map_questions(db))


async def team_detail(db: AsyncSession, team_id: int) -> TeamDetailOut:
    summaries = await team_summaries(db, team_id)
    if not summaries:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    events = await db.scalars(
        select(TeamPathEvent).where(TeamPathEvent.team_id == team_id).order_by(TeamPathEvent.id)
    )
    logs = await db.scalars(select(TeamLog).where(TeamLog.team_id == team_id).order_by(TeamLog.id))
    ledger = await db.scalars(
        select(PointLedger).where(PointLedger.team_id == team_id).order_by(PointLedger.id)
    )
    return TeamDetailOut(
        **summaries[0].model_dump(),
        map=[PathEventOut.model_validate(e) for e in events],
        logs=[TeamLogOut.model_validate(entry) for entry in logs],
        ledger=[LedgerOut.model_validate(row) for row in ledger],
    )


async def team_logs(
    db: AsyncSession,
    team_id: int | None,
    question_id: uuid.UUID | None,
    event: QuestionEvent | None,
    limit: int,
) -> list[TeamLogOut]:
    stmt = select(TeamLog).order_by(TeamLog.id.desc()).limit(limit)
    if team_id is not None:
        stmt = stmt.where(TeamLog.team_id == team_id)
    if question_id is not None:
        stmt = stmt.where(TeamLog.question_id == question_id)
    if event is not None:
        stmt = stmt.where(TeamLog.event == event)
    return [TeamLogOut.model_validate(entry) for entry in await db.scalars(stmt)]


async def audit_trail(db: AsyncSession, action: str | None, limit: int) -> list[AuditOut]:
    stmt = select(AdminAudit).order_by(AdminAudit.id.desc()).limit(limit)
    if action is not None:
        stmt = stmt.where(AdminAudit.action == action)
    return [AuditOut.model_validate(entry) for entry in await db.scalars(stmt)]


async def unblock(db: AsyncSession, question: Question) -> int:
    now = utcnow()
    question.blocked_until = None
    question.blocked_by_team_id = None
    # end waits that were tied to this block
    waiting = await db.scalars(
        select(State).where(State.question_id == question.id, State.wait_until > now)
    )
    cleared = 0
    for state in waiting:
        state.wait_until = None
        cleared += 1
    return cleared
