from fastapi import APIRouter

from app.routers.admin import auth

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
