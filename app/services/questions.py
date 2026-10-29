import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GameState, Question, Team, TeamQuestionState
from app.models.enums import QuestionEvent, QuestionStatus
from app.schemas.question import QuestionOut, QuestionState
from app.services import game_clock, logs, progression, scoring


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")


async def lock_team(db: AsyncSession, team: Team) -> Team:
    return await db.get(Team, team.id, with_for_update=True, populate_existing=True) or team


async def get_state(
    db: AsyncSession, team_id: int, question_id: uuid.UUID, lock: bool = False
) -> TeamQuestionState | None:
    return await db.get(
        TeamQuestionState, (team_id, question_id), with_for_update=lock, populate_existing=lock
    )


async def resolve(
    db: AsyncSession, team: Team, question_id: uuid.UUID
) -> tuple[Question, TeamQuestionState | None, int | None]:
    # unreachable and unknown look the same 
    question = await db.get(Question, question_id)
    if question is None:
        raise _not_found()
    state = await get_state(db, team.id, question_id)
    if state is not None and state.status in progression.DONE:
        return question, state, None
    if not question.enabled:
        raise _not_found()
    path_id = await progression.reachable_path(db, team, question_id)
    if path_id is None:
        raise _not_found()
    return question, state, path_id


async def ensure_state(
    db: AsyncSession, team: Team, question: Question, now: datetime
) -> TeamQuestionState:
    state = await get_state(db, team.id, question.id)
    if state is None:
        state = TeamQuestionState(team_id=team.id, question_id=question.id, viewed_at=now)
        db.add(state)
        logs.log_question(db, team.id, QuestionEvent.VIEW, question.id)
        await db.flush()
    return state


async def unlock(
    db: AsyncSession, question: Question, team: Team, game: GameState, now: datetime
) -> Question:
    if question.unlocked_at is not None:
        return question
    question = (
        await db.get(Question, question.id, with_for_update=True, populate_existing=True)
        or question
    )
    if question.unlocked_at is None:
        question.unlocked_at = now
        question.unlocked_game_seconds = game_clock.active_seconds(game, now)
        question.unlocked_by_team_id = team.id
    return question


def retries_left(question: Question, state: TeamQuestionState | None) -> int:
    if state is None:
        return question.retries
    return max(0, question.retries + state.extra_retries - state.attempts_used)


def blocked_for(question: Question, team_id: int, now: datetime) -> bool:
    return (
        question.blocked_until is not None
        and question.blocked_until > now
        and question.blocked_by_team_id != team_id
    )


def state_label(
    question: Question, state: TeamQuestionState | None, team_id: int, now: datetime
) -> QuestionState:
    if state is not None and state.status == QuestionStatus.SOLVED:
        return "solved"
    if state is not None and state.status == QuestionStatus.SKIPPED:
        return "skipped"
    if blocked_for(question, team_id, now):
        return "blocked"
    if retries_left(question, state) <= 0:
        return "out_of_retries"
    return "active"


def view(
    question: Question,
    state: TeamQuestionState | None,
    team_id: int,
    path_id: int | None,
    active_now: int,
    now: datetime,
) -> QuestionOut:
    hint1_owned = bool(state and state.hint1_owned)
    hint2_owned = bool(state and state.hint2_owned)
    file_url = f"{settings.api_prefix}/question/{question.id}/file" if question.file_path else None
    wait_until = state.wait_until if state and state.wait_until and state.wait_until > now else None
    return QuestionOut(
        question_id=question.id,
        path_id=path_id,
        title=question.title,
        story=question.story,
        monument=question.monument,
        is_final=question.is_final,
        file_url=file_url,
        state=state_label(question, state, team_id, now),
        current_points=scoring.current_points(question, active_now),
        points_awarded=state.points_awarded if state else 0,
        retries_total=question.retries + (state.extra_retries if state else 0),
        retries_left=retries_left(question, state),
        hints_available=[n for n, hint in ((1, question.hint1), (2, question.hint2)) if hint],
        hint1=question.hint1 if hint1_owned else None,
        hint2=question.hint2 if hint2_owned else None,
        blocked_until=question.blocked_until if blocked_for(question, team_id, now) else None,
        wait_until=wait_until,
        first_solve_open=question.first_solved_by_team_id is None,
    )
