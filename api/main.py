import os

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import HTMLResponse


from api.core.handlers import register_exception_handlers
from api.routers import auth, products
from api.security import get_current_username
from api.dependencies import get_db 
from api.limiter import limiter


DEFAULT_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000"


def get_allowed_origins() -> list[str]:
    origins = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app = FastAPI(
    title="Scrabby API",
    description="API de comparación de precios de componentes de PC en tiendas argentinas.",
    version="1.0.0"
)

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return templates.TemplateResponse(
        request=request,
        name="error429.html",
        status_code=429
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


# --- MIDDLEWARES ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- ARCHIVOS ESTÁTICOS Y TEMPLATES ---
app.mount("/static", StaticFiles(directory="api/static"), name="static")
templates = Jinja2Templates(directory="api/templates")


register_exception_handlers(app)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    username = get_current_username(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "username": username},
    )


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check(db=Depends(get_db)) -> dict[str, str]:
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc

    return {"status": "ok"}

# --- ROUTERS ---
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(auth.router, prefix="/users", tags=["users"])
