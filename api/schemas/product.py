from pydantic import BaseModel
from datetime import datetime


class ProductResponse(BaseModel):
    id: int
    store: str | None = None
    name: str
    price: float
    currency: str | None = None
    url: str
    scraped_at: datetime | None = None
    