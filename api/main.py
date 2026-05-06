import logging

from fastapi import HTTPException
from fastapi import FastAPI

from api.routers import products, auth
from database.database import get_connection


logger = logging.getLogger(__name__)


app = FastAPI(
    title="Scrabby API",
    description="API de comparacion de precios de componentes de PC en tiendas argentinas.",
    version="1.0.0"
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a la base de datos",
        ) from exc

    return {"status": "ok"}


app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(auth.router, prefix="/users", tags=["users"])
