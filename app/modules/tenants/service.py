from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User

from .models import Campaign, Client


def create_client(db: Session, name: str, notes: str = "") -> Client:
    client = Client(name=name.strip(), notes=notes)
    db.add(client)
    db.commit()
    return client


def create_campaign(db: Session, client_id: int, name: str, description: str = "") -> Campaign:
    if not db.get(Client, client_id):
        raise ValueError("ismeretlen ügyfél")
    campaign = Campaign(client_id=client_id, name=name.strip(), description=description)
    db.add(campaign)
    db.commit()
    return campaign


def get_client(db: Session, client_id: int) -> Client | None:
    return db.get(Client, client_id)


def get_campaign(db: Session, campaign_id: int) -> Campaign | None:
    return db.get(Campaign, campaign_id)


def clients_for(db: Session, user: User) -> list[Client]:
    visible = access.visible_client_ids(db, user)
    query = select(Client).order_by(Client.name)
    if visible is not None:
        query = query.where(Client.id.in_(visible))
    return list(db.scalars(query))


def campaigns_for(db: Session, user: User, client_id: int) -> list[Campaign]:
    rows = db.scalars(select(Campaign).where(Campaign.client_id == client_id).order_by(Campaign.name))
    return [c for c in rows if access.can_access(db, user, client_id, c.id)]
