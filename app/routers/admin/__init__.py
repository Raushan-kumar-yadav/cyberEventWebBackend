from fastapi import APIRouter

from app.routers.admin import auth, game

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
router.include_router(game.router)
