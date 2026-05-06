import os

from fastapi import HTTPException
import psycopg2

from dotenv import load_dotenv

load_dotenv()

def get_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")

    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a la base de datos",
        ) from exc

    try:
        yield conn
    finally:
        conn.close()
