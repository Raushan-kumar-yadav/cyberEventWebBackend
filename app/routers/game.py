from fastapi import APIRouter

from app.core.clock import utcnow
from app.deps import DB
from app.schemas.game import GameStateOut
from app.services import game_clock

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/state")
async def state(db: DB) -> GameStateOut:
    game = await game_clock.get_game(db)
    return game_clock.public_view(game, utcnow())
