from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import Notification


def add(db: Session, user_id: int, kind: str, text: str, link: str = "") -> Notification:
    note = Notification(user_id=user_id, kind=kind, text=text, link=link)
    db.add(note)
    return note


def unread_count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Notification)
                     .where(Notification.user_id == user_id, Notification.is_read.is_(False))) or 0


def list_for(db: Session, user_id: int, limit: int = 100) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    return list(db.scalars(query.order_by(Notification.id.desc()).limit(limit)))


def mark_all_read(db: Session, user_id: int) -> None:
    db.execute(update(Notification).where(Notification.user_id == user_id).values(is_read=True))
    db.commit()
