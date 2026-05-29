import os
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.database import SessionLocal
from api.dependencies import get_db
from api.limiter import limiter
from api.schemas.auth import DashboardDataResponse
from api.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    TOKEN_SECONDS_EXPIRE,
    create_access_token,
    get_current_username,
)
from api.services.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    get_user_favorites,
)
from database.models import UserFavorite

router = APIRouter()
templates = Jinja2Templates(directory="api/templates")


def _cookie_secure() -> bool:
    return os.getenv("RENDER") is not None


def redirect_to_login(clear_session: bool = False):
    response = RedirectResponse(url="/users/login", status_code=status.HTTP_303_SEE_OTHER)
    if clear_session:
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, secure=_cookie_secure(), samesite="lax")
    return response


def _get_active_user_or_redirect(request: Request):
    username = get_current_username(request)

    if not username:
        has_session_cookie = ACCESS_TOKEN_COOKIE_NAME in request.cookies
        return None, redirect_to_login(clear_session=has_session_cookie)

    db = SessionLocal()
    try:
        user = get_user_by_username(username, db)
    finally:
        db.close()

    if not user or not user.is_active:
        return None, redirect_to_login(clear_session=True)

    return user, None


def _get_active_user_or_raise(request: Request, db: Session):
    username = get_current_username(request)

    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_username(username, db)

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return user


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    username = get_current_username(request)
    return templates.TemplateResponse(request, "login.html", {"request": request, "username": username})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    username = get_current_username(request)
    return templates.TemplateResponse(request, "register.html", {"request": request, "username": username})


@router.post("/register", response_class=HTMLResponse)
@limiter.limit("5/minute")
def register(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request, "register.html", 
            {"request": request, "error": "Las contraseñas no coinciden", "username": username}, 
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        create_user(username, password, db)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request, "register.html",
            {"request": request, "error": exc.detail, "username": username},
            status_code=exc.status_code,
        )

    return RedirectResponse(url="/users/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user, redirect_response = _get_active_user_or_redirect(request)

    if redirect_response:
        return redirect_response

    db = SessionLocal()
    favoritos = []
    error_message = None
    try:
        favoritos = get_user_favorites(user.id, db)
    except Exception:
        error_message = "No se pudieron cargar tus favoritos."
    finally:
        db.close()

    context = {
        "request": request,
        "username": user.username,
        "favoritos": favoritos,
    }

    if error_message:
        context["error"] = error_message

    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/dashboard/data", response_model=DashboardDataResponse)
def dashboard_data(request: Request, db: Session = Depends(get_db)):
    user = _get_active_user_or_raise(request, db)
    favorites = get_user_favorites(user.id, db)

    return {
        "username": user.username,
        "favorites": favorites,
    }


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    user = authenticate_user(username, password, db)

    if not user:
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token({"sub": user.username})

    response = RedirectResponse(url="/users/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        max_age=TOKEN_SECONDS_EXPIRE,
        samesite="lax",
    )

    return response


@router.get("/test-auth")
def test_auth(request: Request):
    username = get_current_username(request)
    db = SessionLocal()
    try:
        if username:
            user = get_user_by_username(username, db)
            return {"authenticated": True, "username": username, "user_id": user.id if user else None}
        else:
            return {"authenticated": False, "username": None}
    finally:
        db.close()


@router.post("/dashboard/favorites/{product_id}")
def add_favorite(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_active_user_or_raise(request, db)
    
    try:
        new_fav = UserFavorite(user_id=user.id, product_id=product_id)
        db.add(new_fav)
        db.commit()
        return {"status": "success", "message": "Producto guardado"}
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()
        if "unique constraint" in error_msg or "duplicate key" in error_msg:
            return {"status": "success", "message": "El producto ya estaba en favoritos"}
        raise HTTPException(status_code=400, detail="No se pudo guardar el favorito debido a un error de integridad")


@router.delete("/dashboard/favorites/{product_id}")
def remove_favorite(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_active_user_or_raise(request, db)
    
    fav = db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id, 
        UserFavorite.product_id == product_id
    ).first()
    
    if fav:
        db.delete(fav)
        db.commit()
        
    return {"status": "success", "message": "Favorito eliminado"}


@router.post("/logout")
def logout():
    return redirect_to_login(clear_session=True)