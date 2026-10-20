from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .models import APPROVED, DRAFT, Rule


def get_rule(db: Session, rule_id: int) -> Rule | None:
    return db.get(Rule, rule_id)


def list_rules(db: Session, scope_type: str, scope_id: int, status: str | None = None) -> list[Rule]:
    query = select(Rule).where(Rule.scope_type == scope_type, Rule.scope_id == scope_id)
    if status:
        query = query.where(Rule.status == status)
    return list(db.scalars(query.order_by(Rule.id)))


def drafts(db: Session, scope_type: str, scope_id: int) -> list[Rule]:
    return list_rules(db, scope_type, scope_id, DRAFT)


def active_rules(db: Session, client_id: int, campaign_id: int, channel_id: int | None = None) -> list[Rule]:
    """A kampányra és opcionálisan csatornára érvényes, jóváhagyott szabályok."""
    scopes = [
        and_(Rule.scope_type == "client", Rule.scope_id == client_id),
        and_(Rule.scope_type == "campaign", Rule.scope_id == campaign_id),
    ]
    if channel_id:
        scopes.append(and_(Rule.scope_type == "channel", Rule.scope_id == channel_id))

    rules = list(db.scalars(select(Rule).where(or_(*scopes), Rule.status == APPROVED).order_by(Rule.id)))
    if channel_id is not None:
        filtered = []
        for r in rules:
            target_ch = (r.applies_to or {}).get("channel_id")
            if target_ch and target_ch != channel_id:
                continue
            filtered.append(r)
        return filtered
    return rules
