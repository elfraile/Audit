"""UI közös részei: sablonmotor, bejelentkezés-kényszer, űrlap-segédek."""
from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user_or_none
from app.modules.accounts.models import User
from app.modules.accounts.roles import ADMIN, EDIT_ROLES

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class LoginRequired(Exception):
    pass


def login_required_handler(request: Request, exc: LoginRequired) -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def ui_user(user: User | None = Depends(current_user_or_none)) -> User:
    if user is None:
        raise LoginRequired()
    return user


def render(request: Request, name: str, user: User | None = None, **context):
    context.update(user=user, can_edit=bool(user and user.role in EDIT_ROLES),
                   is_admin=bool(user and user.role == ADMIN))
    if user:
        with request.app.state.session_factory() as db:
            for provider in request.app.state.ctx.ui_extras:
                context.update(provider(db, user))
    return templates.TemplateResponse(request, name, context)


def back(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


__all__ = ["Session", "get_db", "render", "back", "ui_user", "LoginRequired"]
