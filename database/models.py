from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    store = Column(String(100), index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(12, 2), nullable=False, index=True)
    currency = Column(String(10), server_default="ARS")
    url = Column(String, unique=True, nullable=False)
    scraped_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True
        )

    history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    favorited_by = relationship("UserFavorite", back_populates="product", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10))
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    product = relationship("Product", back_populates="history")

    __table_args__ = (
        Index("ix_price_history_product_id_recorded_at", "product_id", "recorded_at"),
    )

class UserFavorite(Base):
    __tablename__ = "user_favorites"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_favorites_user_product"),
    )