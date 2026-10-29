import hmac
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GameState, Question, Team, TeamLog, TeamQuestionState
from app.models.enums import LedgerReason, PathEvent, QuestionEvent, QuestionStatus
from app.schemas.submission import SubmitIn, SubmitOut
from app.services import actions, game_clock, logs, points, progression, questions, scoring

ANSWER_EVENTS = (QuestionEvent.ANSWER_CORRECT, QuestionEvent.ANSWER_WRONG)


def flag_matches(question: Question, submitted: str) -> bool:
    expected, given = question.flag.strip(), submitted.strip()
    if not question.case_sensitive:
        expected, given = expected.casefold(), given.casefold()
    return hmac.compare_digest(expected.encode(), given.encode())


# counted in the db so the limit holds across workers
async def _check_rate(db: AsyncSession, team_id: int, now: datetime) -> None:
    recent = await db.scalar(
        select(func.count())
        .select_from(TeamLog)
        .where(
            TeamLog.team_id == team_id,
            TeamLog.event.in_(ANSWER_EVENTS),
            TeamLog.created_at > now - timedelta(minutes=1),
        )
    )
    if (recent or 0) >= settings.submit_attempts_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many submissions, slow down")


async def submit(db: AsyncSession, team: Team, question_id: uuid.UUID, body: SubmitIn) -> SubmitOut:
    game, team, now = await actions.begin(db, team)
    await _check_rate(db, team.id, now)
    question, state, path_id = await questions.resolve(db, team, question_id)
    question = (
        await db.get(Question, question.id, with_for_update=True, populate_existing=True)
        or question
    )

    if state is not None and state.status == QuestionStatus.SOLVED:
        return SubmitOut(
            result="correct",
            already_solved=True,
            points_awarded=state.points_awarded,
            points=team.points,
            retries_left=questions.retries_left(question, state),
            first_solver=question.first_solved_by_team_id == team.id,
        )
    if path_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Question was skipped")
    if questions.blocked_for(question, team.id, now):
        return SubmitOut(
            result="block",
            points=team.points,
            retries_left=questions.retries_left(question, state),
            blocked_until=question.blocked_until,
        )

    state = await questions.ensure_state(db, team, question, now)
    question = await questions.unlock(db, question, team, game, now)
    if questions.retries_left(question, state) <= 0:
        await db.commit()
        return SubmitOut(result="out_of_retries", points=team.points, retries_left=0)

    # first answer locks the route
    progression.lock_route(db, team, path_id, now)

    if not flag_matches(question, body.flag):
        state.attempts_used += 1
        logs.log_question(db, team.id, QuestionEvent.ANSWER_WRONG, question.id, submitted=body.flag)
        await db.commit()
        return SubmitOut(
            result="wrong", points=team.points, retries_left=questions.retries_left(question, state)
        )

    return await _solve(db, game, team, question, state, path_id, body, now)


async def _solve(
    db: AsyncSession,
    game: GameState,
    team: Team,
    question: Question,
    state: TeamQuestionState,
    path_id: int,
    body: SubmitIn,
    now: datetime,
) -> SubmitOut:
    awarded = scoring.current_points(question, game_clock.active_seconds(game, now))
    first = question.first_solved_by_team_id is None
    blocked_until = None
    if first:
        question.first_solved_by_team_id = team.id
        question.first_solved_at = now
        # first solver may trade the points for a block
        if body.first_solve_action == "block" and question.block_seconds > 0:
            blocked_until = now + timedelta(seconds=question.block_seconds)
            question.blocked_until = blocked_until
            question.blocked_by_team_id = team.id
            awarded = 0
            logs.log_question(
                db, team.id, QuestionEvent.BLOCKED, question.id, until=blocked_until.isoformat()
            )

    if awarded:
        points.apply(db, team, awarded, LedgerReason.SOLVE, question.id)
    state.status = QuestionStatus.SOLVED
    state.solved_at = now
    state.points_awarded = awarded
    logs.log_question(
        db, team.id, QuestionEvent.ANSWER_CORRECT, question.id, points=awarded, first_solver=first
    )
    logs.log_path(db, team.id, path_id, PathEvent.CLEARED, at=now, question_id=question.id)

    reached = question.is_final and not team.has_reached_delhi
    if reached:
        team.has_reached_delhi = True
        team.reached_delhi_at = now

    next_id = await progression.advance(db, team, path_id, now)
    await db.commit()
    return SubmitOut(
        result="correct",
        points_awarded=awarded,
        points=team.points,
        retries_left=questions.retries_left(question, state),
        first_solver=first,
        blocked_until=blocked_until,
        next_question_id=next_id,
        path_completed=next_id is None,
        reached_delhi=reached,
    )
