import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Request

load_dotenv()

ACCESS_TOKEN_COOKIE_NAME = "access_token"
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# Cambiamos el default a 3600 (1 hora) para mejor UX, podés ajustarlo en tu .env
TOKEN_SECONDS_EXPIRE = int(os.getenv("TOKEN_SECONDS_EXPIRE", "3600"))

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not configured")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_SECONDS_EXPIRE)
    
    # PyJWT usa exactamente la misma sintaxis que tenías
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:  # <-- Usamos la excepción base de PyJWT
        return None


def get_current_username(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        return None

    payload = decode_access_token(token)
    
    # Compactamos la validación final. Si hay payload, extrae el "sub", sino None.
    return payload.get("sub") if payload else None