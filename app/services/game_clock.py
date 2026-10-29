from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import GameState
from app.models.enums import GameStatus
from app.schemas.game import AdminGameStateOut, GameStateOut


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


async def get_game(db: AsyncSession, lock: bool = False) -> GameState:
    game = await db.get(GameState, 1, with_for_update=lock, populate_existing=lock)
    if game is None:
        game = GameState(id=1)
        db.add(game)
        await db.flush()
    return game


def effective_status(game: GameState, now: datetime) -> GameStatus:
    if game.status == GameStatus.RUNNING and game.end_at is not None and now >= game.end_at:
        return GameStatus.ENDED
    return game.status


def active_seconds(game: GameState, now: datetime) -> int:
    if game.start_at is None:
        return 0
    ref = game.paused_at if game.status == GameStatus.PAUSED and game.paused_at else now
    if game.end_at is not None:
        ref = min(ref, game.end_at)
    return max(0, int((ref - game.start_at).total_seconds()) - game.paused_seconds)


def remaining_seconds(game: GameState, now: datetime) -> int | None:
    current = effective_status(game, now)
    if current == GameStatus.NOT_STARTED or game.end_at is None:
        return None
    if current == GameStatus.ENDED:
        return 0
    ref = game.paused_at if current == GameStatus.PAUSED and game.paused_at else now
    return max(0, int((game.end_at - ref).total_seconds()))


def public_view(game: GameState, now: datetime) -> GameStateOut:
    return GameStateOut(
        status=effective_status(game, now),
        start_at=game.start_at,
        end_at=game.end_at,
        remaining_seconds=remaining_seconds(game, now),
        version=game.version,
    )


def admin_view(game: GameState, now: datetime) -> AdminGameStateOut:
    return AdminGameStateOut(
        **public_view(game, now).model_dump(),
        paused_at=game.paused_at,
        paused_seconds=game.paused_seconds,
        active_seconds=active_seconds(game, now),
    )


async def require_started(db: AsyncSession) -> GameState:
    game = await get_game(db)
    if game.status == GameStatus.NOT_STARTED:
        raise _conflict("Game has not started")
    return game


async def require_running(db: AsyncSession) -> GameState:
    game = await get_game(db)
    if effective_status(game, utcnow()) != GameStatus.RUNNING:
        raise _conflict("Game is not running")
    return game


def start(game: GameState, now: datetime, duration_minutes: int) -> None:
    if game.status != GameStatus.NOT_STARTED:
        raise _conflict("Game already started")
    game.status = GameStatus.RUNNING
    game.start_at = now
    game.end_at = now + timedelta(minutes=duration_minutes)
    game.paused_at = None
    game.paused_seconds = 0
    game.version += 1


def pause(game: GameState, now: datetime) -> None:
    if effective_status(game, now) != GameStatus.RUNNING:
        raise _conflict("Game is not running")
    game.status = GameStatus.PAUSED
    game.paused_at = now
    game.version += 1


def resume(game: GameState, now: datetime) -> None:
    if game.status != GameStatus.PAUSED or game.paused_at is None or game.end_at is None:
        raise _conflict("Game is not paused")
    # paused time does not eat game time
    paused = now - game.paused_at
    game.paused_seconds += int(paused.total_seconds())
    game.end_at += paused
    game.status = GameStatus.RUNNING
    game.paused_at = None
    game.version += 1


def end(game: GameState, now: datetime) -> None:
    if game.status == GameStatus.NOT_STARTED or game.end_at is None:
        raise _conflict("Game has not started")
    if game.status == GameStatus.ENDED:
        raise _conflict("Game already ended")
    if game.status == GameStatus.PAUSED:
        resume(game, now)
    game.status = GameStatus.ENDED
    game.end_at = min(game.end_at, now)
    game.version += 1


def extend(game: GameState, now: datetime, minutes: int) -> None:
    if game.status in (GameStatus.NOT_STARTED, GameStatus.ENDED) or game.end_at is None:
        raise _conflict("Game is not in progress")
    new_end = game.end_at + timedelta(minutes=minutes)
    ref = game.paused_at if game.status == GameStatus.PAUSED and game.paused_at else now
    if new_end <= ref:
        raise _conflict("New end time is already in the past")
    game.end_at = new_end
    game.version += 1
