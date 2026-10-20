from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.tenants.guards import ensure_campaign_access

from .deps import back, get_db, render, ui_user

router = APIRouter()


@router.post("/campaigns/{campaign_id}/assets/upload")
async def upload_asset(
    campaign_id: int, file: UploadFile = File(...),
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    content = await file.read()
    asset_service.save_and_ingest(db, campaign_id, file.filename or "asset", content)
    return back(f"/campaigns/{campaign_id}#assets")


@router.post("/campaigns/{campaign_id}/assets/scan")
def scan_folder(
    campaign_id: int, folder_path: str = Form(...),
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    try:
        asset_service.scan_local_folder(db, campaign_id, folder_path)
    except ValueError:
        pass
    return back(f"/campaigns/{campaign_id}#assets")


@router.post("/campaigns/{campaign_id}/assets/url")
def ingest_url(
    campaign_id: int, url: str = Form(...), name: str = Form(""),
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    try:
        asset_service.ingest_url(db, campaign_id, url, name)
    except Exception:
        pass
    return back(f"/campaigns/{campaign_id}#assets")


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: int, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    asset = asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404)
    ensure_campaign_access(db, user, asset.campaign_id)
    latest_run = audit_service.latest_run_for_asset(db, asset_id)
    if latest_run:
        return back(f"/audits/{latest_run.id}")
    return back(f"/campaigns/{asset.campaign_id}#assets")
