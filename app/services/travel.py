from datetime import timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import Team
from app.models.enums import LedgerReason, PathEvent, QuestionEvent
from app.schemas.path import PathCancelOut, PathChangeOut
from app.services import actions, content, game_clock, logs, points, progression, questions, store
from app.services.store import PriceKey


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


async def change_path(
    db: AsyncSession, team: Team, path_id: int, mode: Literal["pay", "wait"]
) -> PathChangeOut:
    _, team, now = await actions.begin(db, team)
    await content.get_path(db, path_id)
    if team.current_path_id == path_id:
        raise _conflict("Already on this path")
    if await progression.current_question_id(db, team, path_id) is None:
        raise _conflict("Path already completed")

    old = team.current_path_id
    if old is None:
        # picking a path while exploring is free
        progression.lock_route(db, team, path_id, now)
        await db.commit()
        return PathChangeOut(
            path_id=path_id,
            mode="free",
            charged=0,
            points=team.points,
            starts_at=now,
            frozen_until=None,
        )

    leaving = await progression.current_question_id(db, team, old)
    if leaving is not None:
        logs.log_question(db, team.id, QuestionEvent.LEAVE, leaving)
    logs.log_path(db, team.id, old, PathEvent.LEFT, at=now)
    team.current_path_id = path_id

    charged = 0
    frozen = None
    if mode == "pay":
        charged = await store.get_price(db, PriceKey.PATH_SWITCH_POINTS)
        if charged:
            points.apply(db, team, -charged, LedgerReason.PATH_SWITCH, note=f"{old}->{path_id}")
        team.switch_from_path_id = None
        logs.log_path(db, team.id, path_id, PathEvent.START, at=now)
    else:
        seconds = await store.get_price(db, PriceKey.PATH_SWITCH_WAIT_SECONDS)
        frozen = now + timedelta(seconds=seconds)
        team.frozen_until = frozen
        team.switch_from_path_id = old
        logs.log_path(db, team.id, path_id, PathEvent.WAIT, at=now)
        logs.log_path(db, team.id, path_id, PathEvent.START, at=frozen)

    await db.commit()
    return PathChangeOut(
        path_id=path_id,
        mode=mode,
        charged=charged,
        points=team.points,
        starts_at=frozen or now,
        frozen_until=frozen if frozen and frozen > now else None,
    )


async def cancel_switch(db: AsyncSession, team: Team, path_id: int) -> PathCancelOut:
    await game_clock.require_running(db)
    team = await questions.lock_team(db, team)
    now = utcnow()
    old = team.switch_from_path_id
    frozen = progression.frozen_until(team, now)
    if not frozen or team.current_path_id != path_id or old is None:
        raise _conflict("No path switch to cancel")

    # back to the old path, no refund
    logs.log_path(db, team.id, path_id, PathEvent.CANCELLED, at=now)
    logs.log_path(db, team.id, old, PathEvent.START, at=now)
    team.current_path_id = old
    team.frozen_until = None
    team.switch_from_path_id = None
    await db.commit()
    return PathCancelOut(path_id=old)
