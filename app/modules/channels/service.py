import fnmatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.assets.models import Asset

from .models import Channel, Deliverable


def create_channel(db: Session, campaign_id: int, name: str, code: str = "other",
                   description: str = "") -> Channel:
    if not name.strip():
        raise ValueError("A csoport neve kötelező")
    ch = Channel(campaign_id=campaign_id, name=name.strip(), code=code.strip().lower() or "other",
                 description=description.strip())
    db.add(ch)
    db.commit()
    return ch


def list_channels(db: Session, campaign_id: int) -> list[Channel]:
    return list(db.scalars(
        select(Channel).where(Channel.campaign_id == campaign_id).order_by(Channel.id)
    ))


def get_channel(db: Session, channel_id: int) -> Channel | None:
    return db.get(Channel, channel_id)


def delete_channel(db: Session, channel_id: int) -> None:
    ch = db.get(Channel, channel_id)
    if ch:
        # Kapcsolódó deliverable-ök törlése
        for d in db.scalars(select(Deliverable).where(Deliverable.channel_id == channel_id)):
            db.delete(d)
        db.delete(ch)
        db.commit()


def create_deliverable(db: Session, channel_id: int, campaign_id: int, name: str,
                       specs: str = "", expected_copy: str = "", post_copy: str = "",
                       file_pattern: str = "") -> Deliverable:
    if not name.strip():
        raise ValueError("A promóciós anyag megnevezése kötelező")
    deliv = Deliverable(
        channel_id=channel_id, campaign_id=campaign_id, name=name.strip(),
        specs=specs.strip(), expected_copy=expected_copy.strip(),
        post_copy=post_copy.strip(), file_pattern=file_pattern.strip()
    )
    db.add(deliv)
    db.commit()
    auto_match_deliverables(db, campaign_id)
    return deliv


def list_deliverables(db: Session, campaign_id: int,
                      channel_id: int | None = None) -> list[Deliverable]:
    q = select(Deliverable).where(Deliverable.campaign_id == campaign_id)
    if channel_id:
        q = q.where(Deliverable.channel_id == channel_id)
    return list(db.scalars(q.order_by(Deliverable.id)))


def get_deliverable(db: Session, deliverable_id: int) -> Deliverable | None:
    return db.get(Deliverable, deliverable_id)


def delete_deliverable(db: Session, deliverable_id: int) -> None:
    deliv = db.get(Deliverable, deliverable_id)
    if deliv:
        db.delete(deliv)
        db.commit()


def link_asset_to_deliverable(db: Session, deliverable_id: int, asset_id: int | None) -> Deliverable:
    deliv = db.get(Deliverable, deliverable_id)
    if not deliv:
        raise ValueError("Várt anyag nem található")
    deliv.asset_id = asset_id
    if asset_id:
        asset = db.get(Asset, asset_id)
        if asset:
            asset.deliverable_id = deliverable_id
            asset.channel_id = deliv.channel_id
    db.commit()
    return deliv


def auto_match_deliverables(db: Session, campaign_id: int) -> int:
    """Összepárosítja a feltöltött kreatívokat a várt anyagokkal minta vagy név alapján."""
    deliverables = list_deliverables(db, campaign_id)
    assets = list(db.scalars(select(Asset).where(Asset.campaign_id == campaign_id)))
    matched_count = 0

    for d in deliverables:
        if d.asset_id:
            continue
        for a in assets:
            if a.deliverable_id:
                continue
            matches = False
            a_name_low = a.name.lower()
            if d.file_pattern:
                pat = d.file_pattern.lower()
                if not pat.startswith("*") and not pat.endswith("*"):
                    pat = f"*{pat}*"
                matches = fnmatch.fnmatch(a_name_low, pat)
            if not matches and len(d.name) > 3:
                d_name_low = d.name.lower()
                matches = d_name_low in a_name_low or a_name_low in d_name_low

            if matches:
                d.asset_id = a.id
                a.deliverable_id = d.id
                a.channel_id = d.channel_id
                matched_count += 1
                break

    if matched_count > 0:
        db.commit()
    return matched_count
