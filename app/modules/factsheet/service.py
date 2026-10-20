from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import bus

from .models import CONFIRMED, PENDING, PROPOSED, Fact


def current_fact(db: Session, campaign_id: int, key: str) -> Fact | None:
    return db.scalar(
        select(Fact).where(Fact.campaign_id == campaign_id, Fact.key == key, Fact.is_current.is_(True))
    )


def _store(db: Session, campaign_id: int, key: str, value: Any, source: str,
           source_date: date | None, status: str, user_id: int | None, current: bool) -> Fact:
    fact = Fact(campaign_id=campaign_id, key=key.strip(), value=value, source=source,
                source_date=source_date, status=status, is_current=current, created_by=user_id)
    db.add(fact)
    return fact


def set_fact(db: Session, campaign_id: int, key: str, value: Any, source: str = "",
             source_date: date | None = None, user_id: int | None = None) -> Fact:
    """Megerősített tény rögzítése; az előző aktuális érték előzménnyé válik."""
    prev = current_fact(db, campaign_id, key)
    if prev:
        prev.is_current = False
    fact = _store(db, campaign_id, key, value, source, source_date, CONFIRMED, user_id, True)
    db.commit()
    bus.publish("fact.changed", campaign_id=campaign_id, key=fact.key, fact_id=fact.id)
    return fact


def open_question(db: Session, campaign_id: int, key: str, note: str = "",
                  user_id: int | None = None) -> Fact:
    """Nyitott pont: aktuális sor érték nélkül. Nem írhat felül megerősített tényt."""
    if current_fact(db, campaign_id, key):
        raise ValueError("ehhez a kulcshoz már van aktuális érték; használj javaslatot")
    fact = _store(db, campaign_id, key, None, note, None, PENDING, user_id, True)
    db.commit()
    return fact


def propose_change(db: Session, campaign_id: int, key: str, value: Any, source: str = "",
                   source_date: date | None = None, user_id: int | None = None) -> Fact:
    """Javasolt módosítás: nem hiteles/nem megerősített forrásból nem lesz automatikusan aktuális."""
    fact = _store(db, campaign_id, key, value, source, source_date, PROPOSED, user_id, False)
    db.commit()
    return fact


def accept_proposal(db: Session, fact_id: int, user_id: int | None = None) -> Fact:
    fact = db.get(Fact, fact_id)
    if not fact or fact.status != PROPOSED:
        raise ValueError("nem javasolt tétel")
    prev = current_fact(db, fact.campaign_id, fact.key)
    if prev:
        prev.is_current = False
    fact.status, fact.is_current = CONFIRMED, True
    db.commit()
    bus.publish("fact.changed", campaign_id=fact.campaign_id, key=fact.key, fact_id=fact.id)
    return fact


def reject_proposal(db: Session, fact_id: int) -> None:
    fact = db.get(Fact, fact_id)
    if fact and fact.status == PROPOSED:
        db.delete(fact)
        db.commit()
