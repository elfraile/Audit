from sqlalchemy.orm import Session

from app.core.clock import utcnow

from . import events
from .models import DONE, OPEN, STATUSES, Comment, Issue


def _issue(db: Session, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise ValueError("ismeretlen tétel")
    return issue


def create_issue(db: Session, campaign_id: int, description: str, asset_ref: str = "", source: str = "",
                 category: str = "unclassified", user_id: int | None = None,
                 asset_id: int | None = None, rule_id: int | None = None) -> Issue:
    if not description.strip():
        raise ValueError("a leírás kötelező")
    issue = Issue(campaign_id=campaign_id, description=description.strip(), asset_ref=asset_ref,
                  source=source, category=category, created_by=user_id,
                  asset_id=asset_id, rule_id=rule_id)
    db.add(issue)
    db.commit()
    events.emit(events.CREATED, db, issue, user_id)
    return issue


def set_status(db: Session, issue_id: int, status: str, user_id: int | None = None) -> Issue:
    if status not in STATUSES:
        raise ValueError(f"ismeretlen állapot: {status}")
    issue = _issue(db, issue_id)
    if issue.status == status:
        return issue
    issue.status = status
    issue.closed_by, issue.closed_at = (None, None) if status == OPEN else (user_id, utcnow())
    db.commit()
    events.emit(events.STATUS_CHANGED, db, issue, user_id)
    return issue


def edit_issue(db: Session, issue_id: int, **changes) -> Issue:
    issue = _issue(db, issue_id)
    for field in ("description", "asset_ref", "source", "category", "asset_id", "rule_id"):
        if field in changes:
            setattr(issue, field, changes[field])
    db.commit()
    return issue


def add_comment(db: Session, issue_id: int, body: str, user_id: int | None = None) -> Comment:
    issue = _issue(db, issue_id)
    if not body.strip():
        raise ValueError("üres megjegyzés")
    comment = Comment(issue_id=issue.id, user_id=user_id, body=body.strip())
    db.add(comment)
    db.commit()
    events.emit(events.COMMENTED, db, issue, user_id, comment=comment)
    return comment


def request_rule(db: Session, issue_id: int, scope_type: str, user_id: int | None = None) -> Issue:
    """Szabályjavaslatot kér a tételből (a szabálymodul kezeli az eseményt)."""
    issue = _issue(db, issue_id)
    if issue.promoted:
        raise ValueError("ebből a tételből már készült szabályjavaslat")
    events.emit(events.RULE_REQUESTED, db, issue, user_id, scope_type=scope_type)
    issue.promoted = True
    db.commit()
    return issue


__all__ = ["create_issue", "set_status", "edit_issue", "add_comment", "request_rule", "DONE"]
