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


def active_rules(db: Session, client_id: int, campaign_id: int) -> list[Rule]:
    """A kampányra érvényes, jóváhagyott szabályok: ügyfél-szintű + kampány-szintű."""
    scope = or_(
        and_(Rule.scope_type == "client", Rule.scope_id == client_id),
        and_(Rule.scope_type == "campaign", Rule.scope_id == campaign_id),
    )
    return list(db.scalars(select(Rule).where(scope, Rule.status == APPROVED).order_by(Rule.id)))
