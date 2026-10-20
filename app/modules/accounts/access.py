"""Hozzáférés-szabályok (ügyfél/kampány szinten)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Grant, User
from .roles import ADMIN


def grant_access(db: Session, user_id: int, client_id: int, campaign_id: int | None = None) -> Grant:
    grant = Grant(user_id=user_id, client_id=client_id, campaign_id=campaign_id)
    db.add(grant)
    db.commit()
    return grant


def revoke_access(db: Session, grant_id: int) -> None:
    grant = db.get(Grant, grant_id)
    if grant:
        db.delete(grant)
        db.commit()


def list_grants(db: Session, user_id: int) -> list[Grant]:
    return list(db.scalars(select(Grant).where(Grant.user_id == user_id)))


def can_access(db: Session, user: User, client_id: int, campaign_id: int | None = None) -> bool:
    """Kampány nélkül: az ügyfél látható-e. Kampánnyal: az adott kampány elérhető-e."""
    if user.role == ADMIN:
        return True
    for grant in db.scalars(select(Grant).where(Grant.user_id == user.id, Grant.client_id == client_id)):
        if campaign_id is None or grant.campaign_id is None or grant.campaign_id == campaign_id:
            return True
    return False


def recipients(db: Session, client_id: int, campaign_id: int, exclude_id: int | None = None) -> list[User]:
    """Azok az aktív felhasználók, akik a kampányt látják (értesítési címzettek)."""
    users = db.scalars(select(User).where(User.is_active.is_(True)))
    return [u for u in users if u.id != exclude_id and can_access(db, u, client_id, campaign_id)]


def visible_client_ids(db: Session, user: User) -> set[int] | None:
    """None = minden ügyfél (admin)."""
    if user.role == ADMIN:
        return None
    return {g.client_id for g in list_grants(db, user.id)}
