from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from api.dependencies import get_db
from api.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    TOKEN_SECONDS_EXPIRE,
    create_access_token,
    get_current_username,
)
from api.services.auth import authenticate_user, get_user_by_username

router = APIRouter()


templates = Jinja2Templates(directory="api/templates")


def redirect_to_login(clear_session: bool = False):
    response = RedirectResponse(url="/users/login", status_code=303)

    if clear_session:
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)

    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db=Depends(get_db),
):
    username = get_current_username(request)

    if not username:
        return redirect_to_login()

    user = get_user_by_username(username, db)

    if not user or not user["is_active"]:
        return redirect_to_login(clear_session=True)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "username": user["username"],
        },
    )


@router.post("/login")
def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db=Depends(get_db),
):
    user = authenticate_user(username, password, db)

    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Usuario o contrasena incorrectos",
            },
            status_code=401,
        )

    token = create_access_token({"sub": user["username"]})

    response = RedirectResponse(url="/users/dashboard", status_code=303)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=TOKEN_SECONDS_EXPIRE,
        samesite="lax",
    )

    return response


@router.post("/logout")
def logout():
    return redirect_to_login(clear_session=True)
