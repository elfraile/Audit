"""Hozzáférés-ellenőrzés szabályokhoz (hatókör -> ügyfél/kampány feloldással)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User
from app.modules.tenants.service import get_campaign

from .queries import get_rule


def ensure_scope_access(db: Session, user: User, scope_type: str, scope_id: int) -> None:
    if scope_type == "client":
        allowed = access.can_access(db, user, scope_id)
    elif scope_type == "campaign":
        campaign = get_campaign(db, scope_id)
        allowed = bool(campaign) and access.can_access(db, user, campaign.client_id, scope_id)
    else:
        raise HTTPException(400, "ismeretlen hatókör")
    if not allowed:
        raise HTTPException(403, "nincs hozzáférés")


def ensure_rule_access(db: Session, user: User, rule_id: int) -> None:
    rule = get_rule(db, rule_id)
    if not rule:
        raise HTTPException(404, "ismeretlen szabály")
    ensure_scope_access(db, user, rule.scope_type, rule.scope_id)
