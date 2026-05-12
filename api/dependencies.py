import psycopg2
from fastapi import HTTPException, status

from database.database import get_connection


def open_db_connection():
    try:
        return get_connection()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        ) from exc
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc


def get_db():
    conn = open_db_connection()

    try:
        yield conn
    finally:
        conn.close()
