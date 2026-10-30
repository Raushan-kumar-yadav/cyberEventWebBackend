from fastapi import APIRouter

from app.routers.admin import auth, content, game, monitor, store, teams

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
router.include_router(game.router)
router.include_router(store.router)
router.include_router(content.router)
router.include_router(monitor.router)
router.include_router(teams.router)
