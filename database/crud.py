from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database.database import SessionLocal
from database.models import Product, PriceHistory

def save_products(products: list[dict]) -> int:
    if not products:
        return 0

    db: Session = SessionLocal()
    inserted = 0

    try:
        for p in products:
            if not p.get("name") or p.get("price") is None or not p.get("url"):
                continue

            # 1. Buscamos el producto
            db_product = db.query(Product).filter(Product.url == p["url"]).first()

            if db_product:
                # LA MAGIA ESTÁ ACÁ: Forzamos la actualización de la fecha manualmente
                db_product.scraped_at = func.now()
                
                # Chequeamos si el precio cambió para guardar el historial
                precio_cambio = db_product.price != p["price"]
                
                # Actualizamos el precio de todos modos
                db_product.price = p["price"]
                
                if precio_cambio:
                    # Solo guardamos historial si el precio realmente cambió
                    history = PriceHistory(
                        product_id=db_product.id,
                        price=p["price"],
                        currency=p.get("currency", "ARS")
                    )
                    db.add(history)
            else:
                # Si el producto es nuevo, lo creamos
                db_product = Product(
                    store=p.get("store"),
                    name=p.get("name"),
                    price=p["price"],
                    currency=p.get("currency", "ARS"),
                    url=p["url"]
                )
                db.add(db_product)
                db.flush() # Flush para obtener el ID
                
                # Guardamos el historial inicial
                history = PriceHistory(
                    product_id=db_product.id,
                    price=p["price"],
                    currency=p.get("currency", "ARS")
                )
                db.add(history)

            inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()