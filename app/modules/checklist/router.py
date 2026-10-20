from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.tenants.guards import ensure_campaign_access

from . import service

router = APIRouter(prefix="/api/campaigns/{campaign_id}/checklist", tags=["checklist"])


class ItemIn(BaseModel):
    label: str
    note: str = ""


def _out(i) -> dict:
    return {"id": i.id, "label": i.label, "note": i.note, "done": i.done}


@router.get("")
def list_items(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return [_out(i) for i in service.list_items(db, campaign_id)]


@router.post("")
def add_item(campaign_id: int, body: ItemIn, user: User = Depends(require_editor),
             db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    try:
        return _out(service.add_item(db, campaign_id, body.label, body.note))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
