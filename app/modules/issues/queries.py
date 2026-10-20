from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import OPEN, Comment, Issue


def get_issue(db: Session, issue_id: int) -> Issue | None:
    return db.get(Issue, issue_id)


def list_issues(db: Session, campaign_id: int, status: str | None = None) -> list[Issue]:
    query = select(Issue).where(Issue.campaign_id == campaign_id)
    if status:
        query = query.where(Issue.status == status)
    return list(db.scalars(query.order_by(Issue.id.desc())))


def open_issues(db: Session, campaign_id: int) -> list[Issue]:
    return list_issues(db, campaign_id, OPEN)


def closed_issues(db: Session, campaign_id: int) -> list[Issue]:
    return [i for i in list_issues(db, campaign_id) if i.status != OPEN]


def comments(db: Session, issue_id: int) -> list[Comment]:
    return list(db.scalars(select(Comment).where(Comment.issue_id == issue_id).order_by(Comment.id)))


def status_counts(db: Session, campaign_ids: list[int]) -> dict[int, Counter]:
    """Kampányonként állapot -> darabszám (ügyfél-szintű összesítőhöz)."""
    result: dict[int, Counter] = {cid: Counter() for cid in campaign_ids}
    for issue in db.scalars(select(Issue).where(Issue.campaign_id.in_(campaign_ids))):
        result[issue.campaign_id][issue.status] += 1
    return result


def recurring_categories(db: Session, campaign_ids: list[int]) -> list[tuple[str, int]]:
    """Visszatérő hibatípusok az ügyfél kampányai között, gyakoriság szerint."""
    rows = db.scalars(select(Issue.category).where(Issue.campaign_id.in_(campaign_ids)))
    return Counter(rows).most_common()
