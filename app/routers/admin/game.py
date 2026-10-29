from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from app.core.clock import utcnow
from app.core.config import settings
from app.deps import DB, CurrentAdmin
from app.models import Admin, GameState
from app.schemas.game import AdminGameStateOut, GameStart, TimeIncrease
from app.services import audit, game_clock

router = APIRouter()


async def _apply(
    db: DB,
    admin: Admin,
    action: str,
    change: Callable[[GameState, datetime], None],
    **payload: Any,
) -> AdminGameStateOut:
    now = utcnow()
    game = await game_clock.get_game(db, lock=True)
    change(game, now)
    audit.record(db, admin.id, action, "game", **payload)
    await db.commit()
    return game_clock.admin_view(game, now)


@router.get("/game")
async def get_state(admin: CurrentAdmin, db: DB) -> AdminGameStateOut:
    game = await game_clock.get_game(db)
    return game_clock.admin_view(game, utcnow())


@router.post("/game/start")
async def start(admin: CurrentAdmin, db: DB, body: GameStart | None = None) -> AdminGameStateOut:
    minutes = (body and body.duration_minutes) or settings.game_duration_minutes
    return await _apply(
        db,
        admin,
        "game_start",
        lambda game, now: game_clock.start(game, now, minutes),
        duration_minutes=minutes,
    )


@router.post("/game/pause")
async def pause(admin: CurrentAdmin, db: DB) -> AdminGameStateOut:
    return await _apply(db, admin, "game_pause", game_clock.pause)


@router.post("/game/resume")
async def resume(admin: CurrentAdmin, db: DB) -> AdminGameStateOut:
    return await _apply(db, admin, "game_resume", game_clock.resume)


@router.post("/game/end")
async def end(admin: CurrentAdmin, db: DB) -> AdminGameStateOut:
    return await _apply(db, admin, "game_end", game_clock.end)


@router.post("/time/increase")
async def increase_time(body: TimeIncrease, admin: CurrentAdmin, db: DB) -> AdminGameStateOut:
    return await _apply(
        db,
        admin,
        "time_increase",
        lambda game, now: game_clock.extend(game, now, body.minutes),
        minutes=body.minutes,
    )
