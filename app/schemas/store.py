from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LocalDatetime

Points = Annotated[int, Field(ge=0, le=10_000)]
Seconds = Annotated[int, Field(ge=0, le=3_600)]


# current store prices
class Prices(BaseModel):
    hint1: int
    hint2: int
    hint12: int
    retry: int
    skip: int
    path_switch_points: int
    path_switch_wait_seconds: int


# partial price update
class PriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hint1: Points | None = None
    hint2: Points | None = None
    hint12: Points | None = None
    retry: Points | None = None
    skip: Points | None = None
    path_switch_points: Points | None = None
    path_switch_wait_seconds: Seconds | None = None


# price change record
class PriceChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    old_value: int
    new_value: int
    admin_id: int | None
    created_at: LocalDatetime


# admin store view
class AdminStoreOut(BaseModel):
    prices: Prices
    history: list[PriceChangeOut]
