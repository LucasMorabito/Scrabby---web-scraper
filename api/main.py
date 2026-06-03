import os
import sentry_sdk
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from api.core.handlers import register_exception_handlers
from api.routers import auth, products
from api.security import get_current_username
from api.dependencies import get_db 
from api.limiter import limiter


DEFAULT_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000"


def get_allowed_origins() -> list[str]:
    origins = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

# --- INICIALIZACIÓN DE SENTRY ---
sentry_dsn = os.getenv("SENTRY_DSN")
print(f"DEBUG: El DSN detectado es: {sentry_dsn}")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )
    print("Sentry activado para monitoreo de errores")
else:
    print("Sentry NO se activó porque no se encontró el DSN")
    
# --- APP LIFESPAN & SERVICES ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    
    FastAPICache.init(RedisBackend(redis_client), prefix="scrabby-cache")
    
    yield
    
    await redis_client.close()


app = FastAPI(
    title="Scrabby API",
    description="API de comparación de precios de componentes de PC en tiendas argentinas.",
    version="1.0.0",
    lifespan=lifespan
)


# --- STATIC FILES & TEMPLATES ---
app.mount("/static", StaticFiles(directory="api/static"), name="static")
templates = Jinja2Templates(directory="api/templates")


# --- EXCEPTION HANDLERS & RATE LIMITING ---
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return templates.TemplateResponse(
        request=request,
        name="error429.html",
        status_code=429
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
register_exception_handlers(app)


# --- MIDDLEWARES ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- CORE ROUTES ---
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


# --- API ROUTERS ---
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(auth.router, prefix="/users", tags=["users"])