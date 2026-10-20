from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.references import service as ref_service
from app.modules.tenants.guards import ensure_campaign_access

from .deps import back, get_db, ui_user

router = APIRouter()


@router.post("/campaigns/{campaign_id}/references")
async def add_reference(
    campaign_id: int, name: str = Form(...), category: str = Form("logo"),
    scope_type: str = Form("campaign"), file: UploadFile = File(...),
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    content = await file.read()
    scope_id = campaign_id if scope_type == "campaign" else int(scope_type)
    ref_service.add_reference(
        db, scope_type if scope_type in ("campaign", "client") else "campaign",
        scope_id, name, category, content, file.filename or "ref.png"
    )
    return back(f"/campaigns/{campaign_id}#references")


@router.post("/campaigns/{campaign_id}/references/{ref_id}/delete")
def delete_reference(
    campaign_id: int, ref_id: int,
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    ref_service.delete_reference(db, ref_id)
    return back(f"/campaigns/{campaign_id}#references")
