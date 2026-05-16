from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import User, Product, UserFavorite
from utils.security import hash_password, verify_password

USERNAME_EXISTS_MESSAGE = "Username already exists"
USERNAME_REQUIRED_MESSAGE = "Username is required"
PASSWORD_REQUIRED_MESSAGE = "Password is required"
PASSWORD_TOO_SHORT_MESSAGE = "Password must be at least 6 characters long"


def get_user_by_username(username: str, db: Session):
    # Magia del ORM: SELECT * FROM users WHERE username = username LIMIT 1
    return db.query(User).filter(User.username == username).first()


def create_user(username: str, password: str, db: Session):
    username = username.strip()

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_REQUIRED_MESSAGE)
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_REQUIRED_MESSAGE)
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_TOO_SHORT_MESSAGE)

    password_hash = hash_password(password)
    
    # Creamos el objeto Python
    new_user = User(username=username, password_hash=password_hash)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        # SQLAlchemy ataja automáticamente si se viola el UNIQUE de username
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=USERNAME_EXISTS_MESSAGE,
        )


def authenticate_user(username: str, password: str, db: Session):
    user = get_user_by_username(username, db)

    if not user or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_user_favorites(user_id: int, db: Session):
    # Magia del ORM: Un JOIN automático entre Products y UserFavorites
    return (
        db.query(Product)
        .join(UserFavorite)
        .filter(UserFavorite.user_id == user_id)
        .order_by(UserFavorite.created_at.desc())
        .all()
    )