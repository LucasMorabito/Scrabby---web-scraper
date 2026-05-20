from datetime import datetime, timezone
from database.connection import SessionLocal
from database.models import Product

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
                
            if "scraped_at" not in p:
                p["scraped_at"] = datetime.now(timezone.utc).isoformat()

            if url in existing_products:
                db_product = existing_products[url]
                db_product.price = p.get("price")
                db_product.scraped_at = p["scraped_at"]
            else:
                new_prod = Product(**p)
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