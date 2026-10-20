"""Hozzáférés-ellenőrzés kampány szinten (közös, minden modul használhatja)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User

from .models import Campaign
from .service import get_campaign


def ensure_campaign_access(db: Session, user: User, campaign_id: int) -> Campaign:
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(404, "ismeretlen kampány")
    if not access.can_access(db, user, campaign.client_id, campaign_id):
        raise HTTPException(403, "nincs hozzáférés")
    return campaign
