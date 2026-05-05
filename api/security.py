import os
from datetime import datetime, timedelta

from fastapi import Request

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

ACCESS_TOKEN_COOKIE_NAME = "access_token"
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_SECONDS_EXPIRE = int(os.getenv("TOKEN_SECONDS_EXPIRE", "900"))

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not configured")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(seconds=TOKEN_SECONDS_EXPIRE)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_username(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        return None

    payload = decode_access_token(token)

    if not payload:
        return None

    username = payload.get("sub")

    if not username:
        return None

    return username
