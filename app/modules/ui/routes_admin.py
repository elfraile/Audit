from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts import access, service
from app.modules.accounts.models import User
from app.modules.accounts.roles import ADMIN, ROLES
from app.modules.tenants import service as tenants

from .deps import back, get_db, render, ui_user

router = APIRouter(prefix="/admin")


def _admin(user: User) -> None:
    if user.role != ADMIN:
        raise HTTPException(403)


@router.get("/users")
def users_page(request: Request, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _admin(user)
    rows = [(u, access.list_grants(db, u.id)) for u in service.list_users(db)]
    return render(request, "users.html", user, rows=rows, roles=ROLES,
                  clients=tenants.clients_for(db, user))


@router.post("/users")
def add_user(email: str = Form(...), name: str = Form(...), password: str = Form(...),
             role: str = Form("viewer"), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _admin(user)
    service.create_user(db, email, name, password, role)
    return back("/admin/users")


@router.post("/users/{user_id}/grants")
def add_grant(user_id: int, client_id: int = Form(...), campaign_id: str = Form(""),
              user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _admin(user)
    access.grant_access(db, user_id, client_id, int(campaign_id) if campaign_id else None)
    return back("/admin/users")
