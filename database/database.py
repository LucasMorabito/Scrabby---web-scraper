import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

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
                    cur.execute("""
                        INSERT INTO products (store, name, price, currency, url)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (url) 
                        DO UPDATE SET 
                            price = EXCLUDED.price,
                            scraped_at = NOW()
                    """, (
                        p.get("store"),
                        p.get("name"),
                        p.get("price"),
                        p.get("currency", "ARS"),
                        p.get("url"),
                    ))
                    inserted += 1
    finally:
        conn.close()

    return inserted