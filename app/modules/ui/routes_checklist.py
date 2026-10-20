from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.checklist import service
from app.modules.tenants.guards import ensure_campaign_access

from .deps import back, get_db, ui_user

router = APIRouter()


def _check(db: Session, user: User, campaign_id: int) -> None:
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)


@router.post("/campaigns/{campaign_id}/checklist")
def add_item(campaign_id: int, label: str = Form(...), note: str = Form(""),
             user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _check(db, user, campaign_id)
    try:
        service.add_item(db, campaign_id, label, note)
    except ValueError:
        pass
    return back(f"/campaigns/{campaign_id}#checklist")


@router.post("/campaigns/{campaign_id}/checklist/{item_id}/{action}")
def item_action(campaign_id: int, item_id: int, action: str, user: User = Depends(ui_user),
                db: Session = Depends(get_db)):
    _check(db, user, campaign_id)
    if action in ("done", "undo"):
        service.set_done(db, item_id, action == "done", user.id)
    elif action == "delete":
        service.delete_item(db, item_id)
    return back(f"/campaigns/{campaign_id}#checklist")
