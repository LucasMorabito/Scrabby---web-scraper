from sqlalchemy import Column, Integer, String, Float, DateTime
# Importamos la Base desde database.py (o donde la tengas definida)
from database.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    store = Column(String, index=True)
    name = Column(String)
    price = Column(Float)
    currency = Column(String, default="ARS")
    url = Column(String, unique=True, index=True)
    scraped_at = Column(DateTime)