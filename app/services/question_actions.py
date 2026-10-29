import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GameState, Question, Team, TeamQuestionState
from app.models.enums import LedgerReason, QuestionEvent, QuestionStatus
from app.schemas.actions import HintOut, RetryOut, SkipOut, WaitOut
from app.services import actions, logs, points, progression, questions, store
from app.services.store import PriceKey


@dataclass
class _Ctx:
    game: GameState
    team: Team
    question: Question
    state: TeamQuestionState
    path_id: int
    now: datetime


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


async def _open(db: AsyncSession, team: Team, question_id: uuid.UUID) -> _Ctx:
    game, team, now = await actions.begin(db, team)
    question, state, path_id = await questions.resolve(db, team, question_id)
    if path_id is None:
        raise _conflict("Question is already finished")
    state = await questions.ensure_state(db, team, question, now)
    question = await questions.unlock(db, question, team, game, now)
    return _Ctx(game, team, question, state, path_id, now)


async def _charge(
    db: AsyncSession, team: Team, key: PriceKey, reason: LedgerReason, question_id: uuid.UUID
) -> int:
    # price read inside the locked transaction
    price = await store.get_price(db, key)
    if price:
        points.apply(db, team, -price, reason, question_id, note=key.value)
    return price


async def buy_hint(db: AsyncSession, team: Team, question_id: uuid.UUID, which: str) -> HintOut:
    ctx = await _open(db, team, question_id)
    question, state, team = ctx.question, ctx.state, ctx.team
    wants1, wants2 = which in ("1", "12"), which in ("2", "12")
    if (wants1 and not question.hint1) or (wants2 and not question.hint2):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hint not available")
    if which == "2" and not state.hint1_owned:
        raise _conflict("Buy hint 1 first")

    new1, new2 = wants1 and not state.hint1_owned, wants2 and not state.hint2_owned
    charged = 0
    if new1 or new2:
        if new1 and new2:
            key, event = PriceKey.HINT12, QuestionEvent.H12_PURCHASED
        elif new1:
            key, event = PriceKey.HINT1, QuestionEvent.H1_PURCHASED
        else:
            key, event = PriceKey.HINT2, QuestionEvent.H2_PURCHASED
        charged = await _charge(db, team, key, LedgerReason.HINT, question.id)
        state.hint1_owned = state.hint1_owned or new1
        state.hint2_owned = state.hint2_owned or new2
        team.powerups_used += int(new1) + int(new2)
        logs.log_question(db, team.id, event, question.id, price=charged)

    await db.commit()
    return HintOut(
        question_id=question.id,
        hint1=question.hint1 if state.hint1_owned else None,
        hint2=question.hint2 if state.hint2_owned else None,
        charged=charged,
        points=team.points,
    )


async def buy_retry(db: AsyncSession, team: Team, question_id: uuid.UUID) -> RetryOut:
    ctx = await _open(db, team, question_id)
    question, state, team = ctx.question, ctx.state, ctx.team
    charged = await _charge(db, team, PriceKey.RETRY, LedgerReason.RETRY, question.id)
    state.extra_retries += 1
    team.powerups_used += 1
    logs.log_question(db, team.id, QuestionEvent.RETRY_PURCHASED, question.id, price=charged)
    await db.commit()
    return RetryOut(
        retries_left=questions.retries_left(question, state), charged=charged, points=team.points
    )


async def skip(db: AsyncSession, team: Team, question_id: uuid.UUID) -> SkipOut:
    ctx = await _open(db, team, question_id)
    question, state, team = ctx.question, ctx.state, ctx.team
    if question.is_final:
        raise _conflict("The final question cannot be skipped")
    charged = await _charge(db, team, PriceKey.SKIP, LedgerReason.SKIP, question.id)
    progression.lock_route(db, team, ctx.path_id, ctx.now)
    state.status = QuestionStatus.SKIPPED
    state.wait_until = None
    logs.log_question(db, team.id, QuestionEvent.SKIPPED, question.id, price=charged)
    next_id = await progression.advance(db, team, ctx.path_id, ctx.now)
    await db.commit()
    return SkipOut(
        charged=charged,
        points=team.points,
        next_question_id=next_id,
        path_completed=next_id is None,
    )


async def set_wait(db: AsyncSession, team: Team, question_id: uuid.UUID, wait: bool) -> WaitOut:
    ctx = await _open(db, team, question_id)
    question, state, team, now = ctx.question, ctx.state, ctx.team, ctx.now
    if wait:
        # wait out another team block
        if not questions.blocked_for(question, team.id, now):
            raise _conflict("Question is not blocked")
        state.wait_until = question.blocked_until
        logs.log_question(
            db, team.id, QuestionEvent.WAIT_APPLY, question.id, until=state.wait_until.isoformat()
        )
    elif state.wait_until and state.wait_until > now:
        state.wait_until = None
        logs.log_question(db, team.id, QuestionEvent.CANCELLED_TIMER, question.id)
    await db.commit()
    return WaitOut(wait_until=state.wait_until if wait else None)


async def cancel_wait(db: AsyncSession, team: Team, question_id: uuid.UUID) -> WaitOut:
    ctx = await _open(db, team, question_id)
    state, team = ctx.state, ctx.team
    if not (state.wait_until and state.wait_until > ctx.now):
        raise _conflict("No active wait")
    state.wait_until = None
    logs.log_question(db, team.id, QuestionEvent.CANCELLED_TIMER, ctx.question.id)
    await db.commit()
    return WaitOut(wait_until=None)
