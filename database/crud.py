from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from database.database import SessionLocal
from database.models import PriceHistory, Product


def _as_utc_datetime(value, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return fallback

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return fallback


def save_products(products: list[dict]) -> int:
    if not products:
        return 0

    scraped_at = datetime.now(timezone.utc)
    product_rows_by_url = {}

    for product in products:
        url = product.get("url")
        if not url:
            continue

        product_rows_by_url[url] = {
            "store": product.get("store"),
            "name": product.get("name"),
            "price": product.get("price"),
            "currency": product.get("currency", "ARS"),
            "url": url,
            "scraped_at": _as_utc_datetime(product.get("scraped_at"), scraped_at),
        }

    product_rows = list(product_rows_by_url.values())

    if not product_rows:
        return 0

    db = SessionLocal()
    try:
        insert_stmt = insert(Product).values(product_rows)
        upsert_stmt = (
            insert_stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "price": insert_stmt.excluded.price,
                    "scraped_at": insert_stmt.excluded.scraped_at,
                },
            )
            .returning(Product.id, Product.price, Product.currency)
        )

        upserted_products = db.execute(upsert_stmt).all()
        recorded_at = datetime.now(timezone.utc)
        price_history_rows = [
            {
                "product_id": row.id,
                "price": row.price,
                "currency": row.currency,
                "recorded_at": recorded_at,
            }
            for row in upserted_products
        ]

        if price_history_rows:
            db.bulk_insert_mappings(PriceHistory, price_history_rows)

        db.commit()
        return len(upserted_products)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
