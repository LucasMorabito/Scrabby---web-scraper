from fastapi import FastAPI

from api.routers import products


app = FastAPI(
    title="Scrabby API",
    description="API de comparacion de precios de componentes de PC en tiendas argentinas.",
    version="1.0.0"
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


app.include_router(products.router, prefix="/products", tags=["products"])
