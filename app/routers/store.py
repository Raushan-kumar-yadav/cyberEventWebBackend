from fastapi import APIRouter

from app.deps import DB
from app.schemas.store import Prices
from app.services import store

router = APIRouter(prefix="/store", tags=["store"])


@router.get("/prices")
async def prices(db: DB) -> Prices:
    return Prices(**await store.get_prices(db))
