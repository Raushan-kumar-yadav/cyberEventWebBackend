from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceChange, StorePrice


class PriceKey(StrEnum):
    HINT1 = "hint1"
    HINT2 = "hint2"
    HINT12 = "hint12"
    RETRY = "retry"
    SKIP = "skip"
    PATH_SWITCH_POINTS = "path_switch_points"
    PATH_SWITCH_WAIT_SECONDS = "path_switch_wait_seconds"


DEFAULT_PRICES: dict[PriceKey, int] = {
    PriceKey.HINT1: 50,
    PriceKey.HINT2: 50,
    PriceKey.HINT12: 80,
    PriceKey.RETRY: 25,
    PriceKey.SKIP: 0,
    PriceKey.PATH_SWITCH_POINTS: 20,
    PriceKey.PATH_SWITCH_WAIT_SECONDS: 180,
}


async def get_prices(db: AsyncSession) -> dict[PriceKey, int]:
    prices = dict(DEFAULT_PRICES)
    for row in await db.scalars(select(StorePrice)):
        if row.key in PriceKey:
            prices[PriceKey(row.key)] = row.value
    return prices


async def get_price(db: AsyncSession, key: PriceKey) -> int:
    row = await db.get(StorePrice, key.value)
    return row.value if row else DEFAULT_PRICES[key]


async def update_prices(
    db: AsyncSession, admin_id: int, changes: dict[PriceKey, int]
) -> dict[PriceKey, tuple[int, int]]:
    current = await get_prices(db)
    applied: dict[PriceKey, tuple[int, int]] = {}
    for key, value in changes.items():
        old = current[key]
        if old == value:
            continue
        row = await db.get(StorePrice, key.value, with_for_update=True)
        if row is None:
            db.add(StorePrice(key=key.value, value=value))
        else:
            row.value = value
        db.add(PriceChange(key=key.value, old_value=old, new_value=value, admin_id=admin_id))
        applied[key] = (old, value)
    return applied
