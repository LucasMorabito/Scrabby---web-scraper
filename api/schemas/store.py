from datetime import datetime

from pydantic import BaseModel


class StoreResponse(BaseModel):
    store: str | None = None
    total: int
    last_scraped: datetime | None = None
