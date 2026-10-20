"""Az issues modul eseményei. Más modulok (értesítés, szabályok) ezekre iratkoznak fel."""
from sqlalchemy.orm import Session

from app.core.events import bus
from app.modules.tenants.service import get_campaign

from .models import Issue

CREATED = "issue.created"
STATUS_CHANGED = "issue.status_changed"
COMMENTED = "issue.commented"
RULE_REQUESTED = "issue.rule_requested"


def emit(name: str, db: Session, issue: Issue, actor_id: int | None, **extra) -> None:
    campaign = get_campaign(db, issue.campaign_id)
    bus.publish(name, db=db, issue=issue, client_id=campaign.client_id if campaign else 0,
                actor_id=actor_id, **extra)
