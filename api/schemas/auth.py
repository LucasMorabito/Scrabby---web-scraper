from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None


class UserInDB(BaseModel):
    id: int
    username: str
    password_hash: str
    is_active: bool
    created_at: datetime


class FavoriteProductResponse(BaseModel):
    id: int
    store: str | None = None
    name: str
    price: float
    currency: str | None = None
    url: str | None = None
    scraped_at: datetime | None = None
    last_recorded_price: float | None = None
    last_recorded_at: datetime | None = None


class DashboardDataResponse(BaseModel):
    username: str
    favorites: list[FavoriteProductResponse]
