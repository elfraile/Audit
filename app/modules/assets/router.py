from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.tenants.guards import ensure_campaign_access

from . import service

router = APIRouter(prefix="/api", tags=["assets"])


class ScanIn(BaseModel):
    folder_path: str


class UrlIn(BaseModel):
    url: str
    name: str = ""


def _out(a) -> dict:
    return {
        "id": a.id, "campaign_id": a.campaign_id, "name": a.name,
        "file_type": a.file_type, "file_size": a.file_size,
        "page_count": a.page_count, "created_at": a.created_at.isoformat()
    }


@router.get("/campaigns/{campaign_id}/assets")
def list_assets(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return [_out(a) for a in service.list_assets(db, campaign_id)]


@router.post("/campaigns/{campaign_id}/assets/upload")
async def upload_asset(
    campaign_id: int, file: UploadFile = File(...),
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    content = await file.read()
    asset = service.save_and_ingest(db, campaign_id, file.filename or "asset", content)
    return _out(asset)


@router.post("/campaigns/{campaign_id}/assets/scan")
def scan_folder(
    campaign_id: int, body: ScanIn,
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    try:
        assets = service.scan_local_folder(db, campaign_id, body.folder_path)
        return [_out(a) for a in assets]
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/campaigns/{campaign_id}/assets/url")
def ingest_url(
    campaign_id: int, body: UrlIn,
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    try:
        asset = service.ingest_url(db, campaign_id, body.url, body.name)
        return _out(asset)
    except Exception as e:
        raise HTTPException(400, f"Hiba a link beolvasásakor: {e}") from e


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    asset = service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Asset nem található")
    ensure_campaign_access(db, user, asset.campaign_id)
    content = service.get_content(db, asset_id)
    data = _out(asset)
    data["plain_text"] = content.plain_text if content else ""
    data["blocks"] = content.blocks if content else []
    return data


@router.get("/assets/{asset_id}/preview")
def get_preview(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    asset = service.get_asset(db, asset_id)
    if not asset or not asset.preview_path or not Path(asset.preview_path).exists():
        raise HTTPException(404, "Előnézet nem található")
    ensure_campaign_access(db, user, asset.campaign_id)
    return FileResponse(asset.preview_path)
