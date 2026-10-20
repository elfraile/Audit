from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CONFIRMED, PENDING, PROPOSED, Fact


def _list(db: Session, campaign_id: int, *conditions) -> list[Fact]:
    query = select(Fact).where(Fact.campaign_id == campaign_id, *conditions).order_by(Fact.key, Fact.id)
    return list(db.scalars(query))


def confirmed_facts(db: Session, campaign_id: int) -> list[Fact]:
    return _list(db, campaign_id, Fact.is_current.is_(True), Fact.status == CONFIRMED)


def open_questions(db: Session, campaign_id: int) -> list[Fact]:
    return _list(db, campaign_id, Fact.is_current.is_(True), Fact.status == PENDING)


def proposals(db: Session, campaign_id: int) -> list[Fact]:
    return _list(db, campaign_id, Fact.status == PROPOSED)


def history(db: Session, campaign_id: int, key: str) -> list[Fact]:
    return _list(db, campaign_id, Fact.key == key, Fact.status != PROPOSED)


def as_mapping(db: Session, campaign_id: int) -> dict:
    """A kampány aktuális, megerősített tényei kulcs -> érték formában (az audit-motor számára)."""
    return {f.key: f.value for f in confirmed_facts(db, campaign_id)}
