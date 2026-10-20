"""Hibalista oldalak: tételfelvétel, részletek, megjegyzések, állapot, szabályjavaslat."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts import service as accounts
from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.issues import queries, service
from app.modules.tenants import service as tenants
from app.modules.tenants.guards import ensure_campaign_access

from .deps import back, get_db, render, ui_user

router = APIRouter()


def _issue(db: Session, user: User, issue_id: int, edit: bool = False):
    issue = queries.get_issue(db, issue_id)
    if not issue:
        raise HTTPException(404)
    ensure_campaign_access(db, user, issue.campaign_id)
    if edit and user.role not in EDIT_ROLES:
        raise HTTPException(403)
    return issue


def _safe(action) -> None:
    try:
        action()
    except ValueError:
        pass


@router.post("/campaigns/{campaign_id}/issues")
def add_issue(campaign_id: int, description: str = Form(...), asset_ref: str = Form(""), source: str = Form(""),
              category: str = Form("unclassified"), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    _safe(lambda: service.create_issue(db, campaign_id, description, asset_ref, source, category, user.id))
    return back(f"/campaigns/{campaign_id}#issues")


@router.get("/issues/{issue_id}")
def issue_page(issue_id: int, request: Request, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    issue = _issue(db, user, issue_id)
    rows = queries.comments(db, issue_id)
    names = accounts.user_names(db, {c.user_id for c in rows if c.user_id})
    campaign = tenants.get_campaign(db, issue.campaign_id)
    return render(request, "issue.html", user, issue=issue, campaign=campaign, comments=rows, names=names,
                  categories=request.app.state.ctx.categories.items())


@router.post("/issues/{issue_id}/comment")
def comment(issue_id: int, body: str = Form(...), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _issue(db, user, issue_id, edit=True)
    _safe(lambda: service.add_comment(db, issue_id, body, user.id))
    return back(f"/issues/{issue_id}")


@router.post("/issues/{issue_id}/status")
def status(issue_id: int, status: str = Form(...), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _issue(db, user, issue_id, edit=True)
    _safe(lambda: service.set_status(db, issue_id, status, user.id))
    return back(f"/issues/{issue_id}")


@router.post("/issues/{issue_id}/edit")
def edit(issue_id: int, description: str = Form(...), asset_ref: str = Form(""), source: str = Form(""),
         category: str = Form("unclassified"), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _issue(db, user, issue_id, edit=True)
    service.edit_issue(db, issue_id, description=description, asset_ref=asset_ref, source=source, category=category)
    return back(f"/issues/{issue_id}")


@router.post("/issues/{issue_id}/promote")
def promote(issue_id: int, scope_type: str = Form("campaign"), user: User = Depends(ui_user),
            db: Session = Depends(get_db)):
    _issue(db, user, issue_id, edit=True)
    _safe(lambda: service.request_rule(db, issue_id, scope_type, user.id))
    return back(f"/issues/{issue_id}")
