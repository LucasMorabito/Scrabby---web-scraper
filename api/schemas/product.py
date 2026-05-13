from pydantic import BaseModel

from datetime import datetime


class ProductResponse(BaseModel):
    id: int
    store: str | None = None
    name: str
    price: float
    currency: str | None = None
    url: str | None = None
    scraped_at: datetime | None = None


class PriceHistoryResponse(BaseModel):
    id: int
    product_id: int
    price: float
    currency: str | None = None
    recorded_at: datetime
