import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Path, PathQuestion, Question, Team, TeamQuestionState
from app.models.enums import PathEvent, QuestionStatus
from app.services import logs

DONE = (QuestionStatus.SOLVED, QuestionStatus.SKIPPED)


def frozen_until(team: Team, now: datetime) -> datetime | None:
    return team.frozen_until if team.frozen_until and team.frozen_until > now else None


async def done_question_ids(db: AsyncSession, team_id: int) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(TeamQuestionState.question_id).where(
            TeamQuestionState.team_id == team_id, TeamQuestionState.status.in_(DONE)
        )
    )
    return set(rows)


async def enabled_questions_by_path(
    db: AsyncSession, path_id: int | None = None
) -> dict[int, list[uuid.UUID]]:
    stmt = (
        select(PathQuestion.path_id, PathQuestion.question_id)
        .join(Question, Question.id == PathQuestion.question_id)
        .where(Question.enabled)
        .order_by(PathQuestion.path_id, PathQuestion.position)
    )
    if path_id is not None:
        stmt = stmt.where(PathQuestion.path_id == path_id)
    grouped: dict[int, list[uuid.UUID]] = defaultdict(list)
    for pid, qid in await db.execute(stmt):
        grouped[pid].append(qid)
    return grouped


def next_question(ordered: list[uuid.UUID], done: set[uuid.UUID]) -> uuid.UUID | None:
    return next((qid for qid in ordered if qid not in done), None)


async def current_question_id(db: AsyncSession, team: Team, path_id: int) -> uuid.UUID | None:
    ordered = (await enabled_questions_by_path(db, path_id)).get(path_id, [])
    return next_question(ordered, await done_question_ids(db, team.id))


async def reachable_path(db: AsyncSession, team: Team, question_id: uuid.UUID) -> int | None:
    # locked teams only reach their path
    done = await done_question_ids(db, team.id)
    by_path = await enabled_questions_by_path(db, team.current_path_id)
    paths = [team.current_path_id] if team.current_path_id else await all_path_ids(db)
    for path_id in paths:
        if next_question(by_path.get(path_id, []), done) == question_id:
            return path_id
    return None


async def all_path_ids(db: AsyncSession) -> list[int]:
    return list(await db.scalars(select(Path.id).order_by(Path.sort_order, Path.id)))


def lock_route(db: AsyncSession, team: Team, path_id: int, now: datetime) -> None:
    if team.current_path_id is None:
        team.current_path_id = path_id
        logs.log_path(db, team.id, path_id, PathEvent.START, at=now)


async def advance(db: AsyncSession, team: Team, path_id: int, now: datetime) -> uuid.UUID | None:
    next_id = await current_question_id(db, team, path_id)
    if next_id is None:
        logs.log_path(db, team.id, path_id, PathEvent.END, at=now)
        team.playthroughs += 1
        team.current_path_id = None
    return next_id
