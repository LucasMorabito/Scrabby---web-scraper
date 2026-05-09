from fastapi import FastAPI, HTTPException, status

from api.core.handlers import register_exception_handlers
from api.routers import auth, products
from database.database import get_connection


app = FastAPI(
    title="Scrabby API",
    description="API de comparacion de precios de componentes de PC en tiendas argentinas.",
    version="1.0.0"
)


register_exception_handlers(app)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check() -> dict[str, str]:
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc

    return {"status": "ok"}


app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(auth.router, prefix="/users", tags=["users"])
