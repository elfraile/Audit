from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow

from .models import ChecklistItem


def add_item(db: Session, campaign_id: int, label: str, note: str = "") -> ChecklistItem:
    if not label.strip():
        raise ValueError("a megnevezés kötelező")
    item = ChecklistItem(campaign_id=campaign_id, label=label.strip(), note=note)
    db.add(item)
    db.commit()
    return item


def set_done(db: Session, item_id: int, done: bool, user_id: int | None = None) -> ChecklistItem:
    item = db.get(ChecklistItem, item_id)
    if not item:
        raise ValueError("ismeretlen elem")
    item.done = done
    item.done_by, item.done_at = (user_id, utcnow()) if done else (None, None)
    db.commit()
    return item


def delete_item(db: Session, item_id: int) -> None:
    item = db.get(ChecklistItem, item_id)
    if item:
        db.delete(item)
        db.commit()


def list_items(db: Session, campaign_id: int) -> list[ChecklistItem]:
    query = select(ChecklistItem).where(ChecklistItem.campaign_id == campaign_id)
    return list(db.scalars(query.order_by(ChecklistItem.id)))
