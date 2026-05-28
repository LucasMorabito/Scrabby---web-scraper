from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.limiter import limiter
from api.schemas.product import PriceHistoryResponse, ProductResponse
from api.schemas.store import StoreResponse
from api.security import get_current_username
from database.models import Product, PriceHistory, User, UserFavorite

router = APIRouter()
templates = Jinja2Templates(directory="api/templates")

ALLOWED_ORDER_BY = {"price", "name", "scraped_at"}
ALLOWED_ORDER_DIR = {"asc", "desc"}
ORDER_BY_ERROR = "Invalid order_by. Allowed values: name, price, scraped_at"
ORDER_DIR_ERROR = "Invalid order_dir. Allowed values: asc, desc"
PRODUCTS_NOT_FOUND = "Products not found"
PRODUCT_NOT_FOUND = "Product not found"


def build_pagination_url(request: Request, page: int, per_page: int) -> str:
    params = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in {"page", "per_page", "limit", "offset"}
    ]
    params.extend([("page", page), ("per_page", per_page)])
    return f"{request.url.path}?{urlencode(params)}"


def build_page_links(request: Request, page: int, total_pages: int, per_page: int) -> list[dict]:
    if total_pages <= 7:
        pages = list(range(1, total_pages + 1))
    else:
        pages = [1]
        start = max(2, page - 2)
        end = min(total_pages - 1, page + 2)

        if start > 2:
            pages.append(None)

        pages.extend(range(start, end + 1))

        if end < total_pages - 1:
            pages.append(None)

        pages.append(total_pages)

    return [
        {
            "number": page_number,
            "url": build_pagination_url(request, page_number, per_page) if page_number else None,
            "is_current": page_number == page,
            "is_ellipsis": page_number is None,
        }
        for page_number in pages
    ]


@router.get("/", response_model=list[ProductResponse])
@limiter.limit("30/minute")
def get_products(
    request: Request,
    search: str | None = None,
    store: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    limit: int | None = Query(None, ge=1),
    offset: int | None = Query(None, ge=0),
    order_by: str = "price",
    order_dir: str = "asc",
    db: Session = Depends(get_db)
):
    if order_by not in ALLOWED_ORDER_BY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ORDER_BY_ERROR)

    if order_dir not in ALLOWED_ORDER_DIR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ORDER_DIR_ERROR)

    # 1. Iniciamos la consulta base
    query = db.query(Product)
    
    # 2. Aplicamos filtros dinámicamente
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if store:
        query = query.filter(Product.store.in_(store))

    total_products = query.count()
    total_pages = max((total_products + per_page - 1) // per_page, 1)
    page = min(page, total_pages)

    effective_limit = limit or per_page
    effective_offset = offset if offset is not None else (page - 1) * per_page

    # 3. Aplicamos el ordenamiento dinámico
    order_column = getattr(Product, order_by)
    if order_dir == "desc":
        order_column = order_column.desc()
    else:
        order_column = order_column.asc()

    # 4. Ejecutamos paginación y obtenemos resultados
    results = query.order_by(order_column).offset(effective_offset).limit(effective_limit).all()

    # 5. Lógica para el Frontend (HTML)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        username = get_current_username(request)
        user_favorites = []
        
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                favs = db.query(UserFavorite.product_id).filter(UserFavorite.user_id == user.id).all()
                # favs es una lista de tuplas ej: [(1,), (4,)], extraemos el primer elemento
                user_favorites = [f[0] for f in favs]
        
        return templates.TemplateResponse(
            request,
            "products.html",
            {
                "request": request,
                "products": results,
                "search": search,
                "store": store,
                "order_by": order_by,
                "order_dir": order_dir,
                "username": username,
                "user_favorites": user_favorites,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_products": total_products,
                    "total_pages": total_pages,
                    "has_previous": page > 1,
                    "has_next": page < total_pages,
                    "previous_url": build_pagination_url(request, page - 1, per_page) if page > 1 else None,
                    "next_url": build_pagination_url(request, page + 1, per_page) if page < total_pages else None,
                    "page_links": build_page_links(request, page, total_pages, per_page),
                },
            },
        )

    # 6. Lógica para la API (JSON)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCTS_NOT_FOUND)

    return results


@router.get("/compare/", response_model=dict[str, list[ProductResponse]])
@limiter.limit("30/minute")
def compare_products(request: Request, query: str, db: Session = Depends(get_db)):
    results = db.query(Product).filter(Product.name.ilike(f"%{query}%")).order_by(Product.price.asc()).all()

    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCTS_NOT_FOUND)

    grouped = {}
    for row in results:
        grouped.setdefault(row.store, []).append(row)

    return grouped


@router.get("/stores/", response_model=list[StoreResponse])
def get_stores(db: Session = Depends(get_db)):
    # Usamos las funciones de agregación de SQLAlchemy
    results = db.query(
        Product.store,
        func.count(Product.id).label("total"),
        func.max(Product.scraped_at).label("last_scraped")
    ).group_by(Product.store).all()

    # Convertimos los Row de SQLAlchemy a diccionarios para el schema de Pydantic
    return [{"store": r.store, "total": r.total, "last_scraped": r.last_scraped} for r in results]


@router.get("/cheapest/", response_model=list[ProductResponse])
def get_cheapest_products(db: Session = Depends(get_db)):
    # El equivalente exacto a DISTINCT ON de Postgres
    results = db.query(Product).distinct(Product.store).order_by(Product.store, Product.price.asc()).all()
    return results


@router.get("/{id}/history", response_model=list[PriceHistoryResponse])
def get_product_price_history(id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    # Verificamos si el producto existe
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)

    # Traemos el historial
    history = db.query(PriceHistory).filter(PriceHistory.product_id == id)\
                .order_by(PriceHistory.recorded_at.asc())\
                .offset(offset).limit(limit).all()
    return history


@router.get("/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db: Session = Depends(get_db)):
    result = db.query(Product).filter(Product.id == id).first()
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
        
    return result
