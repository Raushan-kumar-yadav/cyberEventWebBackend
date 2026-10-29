from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, CurrentAdmin
from app.models import PriceChange
from app.schemas.store import AdminStoreOut, PriceChangeOut, Prices, PriceUpdate
from app.services import audit, game_clock, store
from app.services.store import PriceKey

router = APIRouter()


async def _view(db: DB) -> AdminStoreOut:
    history = await db.scalars(select(PriceChange).order_by(PriceChange.id.desc()).limit(50))
    return AdminStoreOut(
        prices=Prices(**await store.get_prices(db)),
        history=[PriceChangeOut.model_validate(change) for change in history],
    )


@router.get("/store")
async def get_store(admin: CurrentAdmin, db: DB) -> AdminStoreOut:
    return await _view(db)


@router.patch("/store")
async def update_store(body: PriceUpdate, admin: CurrentAdmin, db: DB) -> AdminStoreOut:
    changes = {PriceKey(key): value for key, value in body.model_dump(exclude_none=True).items()}
    applied = await store.update_prices(db, admin.id, changes)
    if applied:
        # teams refetch prices on version change
        game = await game_clock.get_game(db, lock=True)
        game.version += 1
        audit.record(
            db,
            admin.id,
            "price_update",
            "store",
            **{key.value: {"old": old, "new": new} for key, (old, new) in applied.items()},
        )
        await db.commit()
    return await _view(db)
