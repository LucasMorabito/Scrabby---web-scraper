from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db
from api.schemas.product import ProductResponse
from api.schemas.store import StoreResponse


router = APIRouter()


ALLOWED_ORDER_BY = {"price", "name", "scraped_at"}
ALLOWED_ORDER_DIR = {"asc", "desc"}


def _fetch_as_dicts(cur) -> list[dict]:
    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]
    return [dict(zip(column_names, row)) for row in rows]


@router.get("/", response_model=list[ProductResponse])
def get_products(
    search: str | None = None,
    store: str | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str = "price",
    order_dir: str = "asc",
    db=Depends(get_db)
):
    cur = db.cursor()

    try:
        if order_by not in ALLOWED_ORDER_BY:
            raise HTTPException(status_code=400, detail="order_by invalido")

        if order_dir not in ALLOWED_ORDER_DIR:
            raise HTTPException(status_code=400, detail="order_dir invalido")

        base_query = "SELECT id, store, name, price, currency, url, scraped_at FROM products"
        conditions = []
        values = []

        if search:
            conditions.append("name ILIKE %s")
            values.append(f"%{search}%")

        if store:
            conditions.append("store = %s")
            values.append(store)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += f" ORDER BY {order_by} {order_dir.upper()} LIMIT %s OFFSET %s"
        values.extend([limit, offset])

        cur.execute(base_query, tuple(values))
        results = _fetch_as_dicts(cur)

        if not results:
            raise HTTPException(status_code=404, detail="No se encontraron productos")

        return results

    finally:
        cur.close()


@router.get("/compare/", response_model=dict[str, list[ProductResponse]])
def compare_products(query: str, db=Depends(get_db)):
    cur = db.cursor()

    try:
        query_sql = """
            SELECT id, store, name, price, currency, url, scraped_at
            FROM products
            WHERE name ILIKE %s
            ORDER BY price ASC
        """

        cur.execute(query_sql, (f"%{query}%",))
        results = _fetch_as_dicts(cur)

        if not results:
            raise HTTPException(status_code=404, detail="No se encontraron productos")

        grouped: dict[str, list[dict]] = {}
        for row in results:
            grouped.setdefault(row["store"], []).append(row)

        return grouped

    finally:
        cur.close()


@router.get("/stores/", response_model=list[StoreResponse])
def get_stores(db=Depends(get_db)):
    cur = db.cursor()

    try:
        query_sql = """
            SELECT store, COUNT(*) as total, MAX(scraped_at) as last_scraped
            FROM products
            GROUP BY store
        """

        cur.execute(query_sql)
        return _fetch_as_dicts(cur)

    finally:
        cur.close()


@router.get("/cheapest/", response_model=list[ProductResponse])
def get_cheapest_products(db=Depends(get_db)):
    cur = db.cursor()

    try:
        query_sql = """
            SELECT DISTINCT ON (store) id, store, name, price, currency, url, scraped_at
            FROM products
            ORDER BY store, price ASC
        """

        cur.execute(query_sql)
        return _fetch_as_dicts(cur)

    finally:
        cur.close()


@router.get("/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db=Depends(get_db)):
    cur = db.cursor()

    try:
        query_sql = """
            SELECT id, store, name, price, currency, url, scraped_at
            FROM products
            WHERE id = %s
        """

        cur.execute(query_sql, (id,))
        results = _fetch_as_dicts(cur)

        if not results:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        return results[0]

    finally:
        cur.close()
