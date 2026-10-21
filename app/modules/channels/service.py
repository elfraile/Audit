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


def get_channel_summary(db: Session, channel_id: int, campaign_id: int) -> dict:
    from app.modules.audits.models import FAILED, PASSED, AuditRun
    from app.modules.issues.models import Issue, OPEN

    deliverables = list_deliverables(db, campaign_id, channel_id)
    total_delivs = len(deliverables)
    assigned_delivs = len([d for d in deliverables if d.asset_id])
    missing_delivs = total_delivs - assigned_delivs

    channel_assets = list(db.scalars(
        select(Asset).where(Asset.campaign_id == campaign_id, Asset.channel_id == channel_id)
    ))

    failed_count = 0
    passed_count = 0
    for a in channel_assets:
        last_run = db.scalar(
            select(AuditRun).where(AuditRun.asset_id == a.id).order_by(AuditRun.id.desc())
        )
        if last_run:
            if last_run.status == FAILED:
                failed_count += 1
            elif last_run.status == PASSED:
                passed_count += 1

    asset_ids = {a.id for a in channel_assets}
    open_issues = list(db.scalars(
        select(Issue).where(
            Issue.campaign_id == campaign_id,
            Issue.status == OPEN,
            Issue.asset_id.in_(asset_ids) if asset_ids else False
        )
    )) if asset_ids else []

    status = "ready"
    if failed_count > 0 or len(open_issues) > 0:
        status = "failed"
    elif missing_delivs > 0 or (total_delivs > 0 and assigned_delivs < total_delivs):
        status = "pending"
    elif total_delivs == 0:
        status = "empty"

    return {
        "channel_id": channel_id,
        "total": total_delivs,
        "assigned": assigned_delivs,
        "missing": missing_delivs,
        "failed": failed_count,
        "passed": passed_count,
        "open_issues": len(open_issues),
        "status": status,
    }


def upload_to_deliverable(db: Session, campaign_id: int, deliverable_id: int,
                          filename: str, data: bytes, user_id: int | None = None):
    from app.modules.assets.service import save_and_ingest
    from app.modules.audits.service import run_audit

    deliv = db.get(Deliverable, deliverable_id)
    if not deliv or deliv.campaign_id != campaign_id:
        raise ValueError("Várt promóciós anyag nem található")

    asset = save_and_ingest(db, campaign_id, filename, data)
    asset.channel_id = deliv.channel_id
    asset.deliverable_id = deliv.id
    deliv.asset_id = asset.id
    db.commit()

    run = run_audit(db, campaign_id, asset.id, user_id=user_id)
    return asset, run


def unlink_deliverable_asset(db: Session, campaign_id: int, deliverable_id: int) -> None:
    deliv = db.get(Deliverable, deliverable_id)
    if not deliv or deliv.campaign_id != campaign_id:
        raise ValueError("Várt promóciós anyag nem található")

    if deliv.asset_id:
        asset = db.get(Asset, deliv.asset_id)
        if asset:
            asset.deliverable_id = None
        deliv.asset_id = None
        db.commit()

