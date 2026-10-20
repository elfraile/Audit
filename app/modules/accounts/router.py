from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db

from . import access, service
from .deps import current_user, require_admin
from .models import User

router = APIRouter(prefix="/api", tags=["accounts"])


class LoginIn(BaseModel):
    email: str
    password: str


class UserIn(BaseModel):
    email: str
    name: str
    password: str
    role: str = "viewer"


class GrantIn(BaseModel):
    client_id: int
    campaign_id: int | None = None


def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = service.authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(401, "hibás belépési adatok")
    request.session["user_id"] = user.id
    return _user_out(user)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _user_out(user)


@router.get("/users", dependencies=[Depends(require_admin)])
def users(db: Session = Depends(get_db)):
    return [_user_out(u) for u in service.list_users(db)]


@router.post("/users", dependencies=[Depends(require_admin)])
def add_user(body: UserIn, db: Session = Depends(get_db)):
    try:
        return _user_out(service.create_user(db, body.email, body.name, body.password, body.role))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/users/{user_id}/grants", dependencies=[Depends(require_admin)])
def add_grant(user_id: int, body: GrantIn, db: Session = Depends(get_db)):
    grant = access.grant_access(db, user_id, body.client_id, body.campaign_id)
    return {"id": grant.id}
