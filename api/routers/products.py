from fastapi import APIRouter, Depends
from api.dependencies import get_db
from api.schemas.product import ProductResponse

router = APIRouter()

@router.get("/", response_model=list[ProductResponse])
def get_products(search: str | None = None, db=Depends(get_db)):
    cur = db.cursor()
    
    try:
        if search:
            query_sql = "SELECT id, store, name, price, currency, url, scraped_at FROM products WHERE name ILIKE %s"
            cur.execute(query_sql, (f"%{search}%",))
        
        # si no especifica nada:
        else:
            query_sql = "SELECT id, store, name, price, currency, url, scraped_at FROM products"
            cur.execute(query_sql)

        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        results = [dict(zip(column_names, row)) for row in rows]
        
        return results
        
    finally:
        # Cierra el cursor siempre
        cur.close()