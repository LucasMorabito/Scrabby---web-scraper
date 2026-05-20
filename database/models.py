from datetime import datetime, timezone
from database.database import SessionLocal
from database.models import Product

PRODUCT_FIELDS = {"store", "name", "price", "currency", "url", "scraped_at"}

def _to_product_dict(p: dict) -> dict:
    """Filtra solo los campos que acepta el modelo Product."""
    result = {k: v for k, v in p.items() if k in PRODUCT_FIELDS}
    
    # Garantiza que scraped_at siempre sea un datetime, no un string
    scraped_at = result.get("scraped_at")
    if scraped_at is None:
        result["scraped_at"] = datetime.now(timezone.utc)
    elif isinstance(scraped_at, str):
        try:
            result["scraped_at"] = datetime.fromisoformat(scraped_at)
        except ValueError:
            result["scraped_at"] = datetime.now(timezone.utc)
    
    return result

def save_products(products: list[dict]) -> int:
    if not products:
        return 0

    db = SessionLocal()
    try:
        existing_products = {p.url: p for p in db.query(Product).all()}
        inserted_count = 0

        for p in products:
            url = p.get("url")
            if not url:
                continue

            clean = _to_product_dict(p)

            if url in existing_products:
                db_product = existing_products[url]
                db_product.price = clean.get("price")
                db_product.scraped_at = clean["scraped_at"]
            else:
                new_prod = Product(**clean)
                db.add(new_prod)
                existing_products[url] = new_prod
                inserted_count += 1

        db.commit()
        return inserted_count
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()