from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.tenants.guards import ensure_campaign_access

from . import queries, service

router = APIRouter(prefix="/api", tags=["issues"])


class IssueIn(BaseModel):
    description: str
    asset_ref: str = ""
    source: str = ""
    category: str = "unclassified"


class StatusIn(BaseModel):
    status: str


class CommentIn(BaseModel):
    body: str


class PromoteIn(BaseModel):
    scope_type: str = "campaign"


def _out(i) -> dict:
    return {"id": i.id, "campaign_id": i.campaign_id, "description": i.description,
            "asset_ref": i.asset_ref, "source": i.source, "category": i.category,
            "status": i.status, "promoted": i.promoted}


def _load(db: Session, user: User, issue_id: int):
    issue = queries.get_issue(db, issue_id)
    if not issue:
        raise HTTPException(404, "ismeretlen tétel")
    ensure_campaign_access(db, user, issue.campaign_id)
    return issue


def _run(action):
    try:
        return action()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/campaigns/{campaign_id}/issues")
def list_issues(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return [_out(i) for i in queries.list_issues(db, campaign_id)]


@router.post("/campaigns/{campaign_id}/issues")
def add_issue(campaign_id: int, body: IssueIn, user: User = Depends(require_editor),
              db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    return _out(_run(lambda: service.create_issue(db, campaign_id, body.description, body.asset_ref,
                                                  body.source, body.category, user.id)))


@router.post("/issues/{issue_id}/status")
def set_status(issue_id: int, body: StatusIn, user: User = Depends(require_editor),
               db: Session = Depends(get_db)):
    _load(db, user, issue_id)
    return _out(_run(lambda: service.set_status(db, issue_id, body.status, user.id)))


@router.post("/issues/{issue_id}/comments")
def add_comment(issue_id: int, body: CommentIn, user: User = Depends(require_editor),
                db: Session = Depends(get_db)):
    _load(db, user, issue_id)
    comment = _run(lambda: service.add_comment(db, issue_id, body.body, user.id))
    return {"id": comment.id}


@router.post("/issues/{issue_id}/promote")
def promote(issue_id: int, body: PromoteIn, user: User = Depends(require_editor),
            db: Session = Depends(get_db)):
    _load(db, user, issue_id)
    return _out(_run(lambda: service.request_rule(db, issue_id, body.scope_type, user.id)))
