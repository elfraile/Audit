from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User
from app.modules.accounts.roles import ADMIN, EDIT_ROLES
from app.modules.tenants import service

from .deps import back, get_db, render, ui_user

router = APIRouter()


@router.get("/")
def home(request: Request, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    clients = [(c, service.campaigns_for(db, user, c.id)) for c in service.clients_for(db, user)]
    return render(request, "home.html", user, clients=clients)


@router.post("/clients")
def add_client(name: str = Form(...), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    if user.role != ADMIN:
        raise HTTPException(403)
    try:
        service.create_client(db, name)
    except IntegrityError:
        db.rollback()
    return back("/")


@router.post("/clients/{client_id}/campaigns")
def add_campaign(client_id: int, name: str = Form(...), user: User = Depends(ui_user),
                 db: Session = Depends(get_db)):
    if user.role not in EDIT_ROLES or not access.can_access(db, user, client_id):
        raise HTTPException(403)
    campaign = service.create_campaign(db, client_id, name)
    return back(f"/campaigns/{campaign.id}")
