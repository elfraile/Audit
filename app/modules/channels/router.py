from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.tenants.guards import ensure_campaign_access

from . import service

router = APIRouter(prefix="/api", tags=["channels"])


class ChannelIn(BaseModel):
    name: str
    code: str = "other"
    description: str = ""


class DeliverableIn(BaseModel):
    name: str
    specs: str = ""
    expected_copy: str = ""
    post_copy: str = ""
    file_pattern: str = ""


@router.get("/campaigns/{campaign_id}/channels")
def list_channels(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return [
        {"id": c.id, "name": c.name, "code": c.code, "description": c.description}
        for c in service.list_channels(db, campaign_id)
    ]


@router.post("/campaigns/{campaign_id}/channels")
def create_channel(
    campaign_id: int, body: ChannelIn,
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    try:
        c = service.create_channel(db, campaign_id, body.name, body.code, body.description)
        return {"id": c.id, "name": c.name, "code": c.code, "description": c.description}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/campaigns/{campaign_id}/deliverables")
def list_deliverables(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return [
        {
            "id": d.id, "channel_id": d.channel_id, "name": d.name, "specs": d.specs,
            "expected_copy": d.expected_copy, "post_copy": d.post_copy,
            "file_pattern": d.file_pattern, "asset_id": d.asset_id
        }
        for d in service.list_deliverables(db, campaign_id)
    ]


@router.post("/campaigns/{campaign_id}/channels/{channel_id}/deliverables")
def create_deliverable(
    campaign_id: int, channel_id: int, body: DeliverableIn,
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    try:
        d = service.create_deliverable(
            db, channel_id, campaign_id, body.name, body.specs,
            body.expected_copy, body.post_copy, body.file_pattern
        )
        return {"id": d.id, "name": d.name, "channel_id": d.channel_id, "asset_id": d.asset_id}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
