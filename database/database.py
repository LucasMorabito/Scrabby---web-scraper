import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg2.connect(database_url)


def save_products(products: list[dict]) -> int:
    """
    Guarda la lista de productos en la base de datos.
    Devuelve cuántos se insertaron.
    """
    if not products:
        return 0

    conn = get_connection()
    inserted = 0

    try:
        with conn:
            with conn.cursor() as cur:
                for p in products:
                    if not p.get("name") or p.get("price") is None or not p.get("url"):
                        continue

                    cur.execute("""
                        INSERT INTO products (store, name, price, currency, url)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (url) 
                        DO UPDATE SET 
                            price = EXCLUDED.price,
                            scraped_at = NOW()
                        RETURNING id
                    """, (
                        p.get("store"),
                        p.get("name"),
                        p.get("price"),
                        p.get("currency", "ARS"),
                        p.get("url"),
                    ))

                    product_id = cur.fetchone()[0]
                    cur.execute("""
                        INSERT INTO price_history (product_id, price, currency)
                        VALUES (%s, %s, %s)
                    """, (
                        product_id,
                        p.get("price"),
                        p.get("currency", "ARS"),
                    ))
                    inserted += 1
    finally:
        conn.close()

    return inserted
