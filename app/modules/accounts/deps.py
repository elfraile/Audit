"""FastAPI függőségek: aktuális felhasználó és szerepkör-ellenőrzés."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db

from .models import User
from .roles import ADMIN, EDIT_ROLES
from .service import get_user


def current_user_or_none(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    user = get_user(db, user_id) if user_id else None
    return user if user and user.is_active else None


def current_user(user: User | None = Depends(current_user_or_none)) -> User:
    if user is None:
        raise HTTPException(401, "bejelentkezés szükséges")
    return user


def require_editor(user: User = Depends(current_user)) -> User:
    if user.role not in EDIT_ROLES:
        raise HTTPException(403, "szerkesztői jogosultság szükséges")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != ADMIN:
        raise HTTPException(403, "adminisztrátori jogosultság szükséges")
    return user
