from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts import access
from app.modules.accounts.deps import current_user, require_admin, require_editor
from app.modules.accounts.models import User

from . import service

router = APIRouter(prefix="/api", tags=["tenants"])


class ClientIn(BaseModel):
    name: str
    notes: str = ""


class CampaignIn(BaseModel):
    name: str
    description: str = ""


@router.get("/clients")
def list_clients(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name} for c in service.clients_for(db, user)]


@router.post("/clients", dependencies=[Depends(require_admin)])
def add_client(body: ClientIn, db: Session = Depends(get_db)):
    try:
        client = service.create_client(db, body.name, body.notes)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(400, "ilyen nevű ügyfél már van") from exc
    return {"id": client.id, "name": client.name}


@router.get("/clients/{client_id}/campaigns")
def list_campaigns(client_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not access.can_access(db, user, client_id):
        raise HTTPException(403, "nincs hozzáférés")
    return [{"id": c.id, "name": c.name} for c in service.campaigns_for(db, user, client_id)]


@router.post("/clients/{client_id}/campaigns")
def add_campaign(client_id: int, body: CampaignIn, user: User = Depends(require_editor),
                 db: Session = Depends(get_db)):
    if not access.can_access(db, user, client_id):
        raise HTTPException(403, "nincs hozzáférés")
    try:
        campaign = service.create_campaign(db, client_id, body.name, body.description)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"id": campaign.id, "name": campaign.name}
