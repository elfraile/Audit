"""Szabálykártya-műveletek a kampányoldalról (kinyerés, jóváhagyás, szerkesztés)."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.rules import lifecycle, suggest
from app.modules.rules.access import ensure_rule_access, ensure_scope_access

from .deps import back, get_db, ui_user

router = APIRouter()


def _editor(user: User) -> None:
    if user.role not in ("admin", "editor"):
        raise HTTPException(403)


@router.post("/campaigns/{campaign_id}/rules/suggest")
def suggest_rules(campaign_id: int, request: Request, text: str = Form(...), scope_type: str = Form("campaign"),
                  scope_id: int = Form(0), source: str = Form(""), user: User = Depends(ui_user),
                  db: Session = Depends(get_db)):
    _editor(user)
    scope_id = scope_id if scope_type == "client" else campaign_id
    ensure_scope_access(db, user, scope_type, scope_id)
    ctx = request.app.state.ctx
    extractor = ctx.extractors.get(ctx.settings.extractor)(ctx.settings)
    suggest.suggest_rules(db, extractor, ctx.categories.keys(), scope_type, scope_id, text, source, user.id)
    return back(f"/campaigns/{campaign_id}")


@router.post("/campaigns/{campaign_id}/rules/{rule_id}/{action}")
def rule_action(campaign_id: int, rule_id: int, action: str, text: str = Form(""),
                category: str = Form(""), severity: str = Form(""), user: User = Depends(ui_user),
                db: Session = Depends(get_db)):
    _editor(user)
    ensure_rule_access(db, user, rule_id)
    try:
        if action == "edit":
            changes = {k: v for k, v in (("text", text), ("category", category), ("severity", severity)) if v}
            lifecycle.edit_rule(db, rule_id, user.id, **changes)
        elif action == "approve":
            lifecycle.approve(db, rule_id, user.id)
        elif action == "reject":
            lifecycle.reject(db, rule_id)
        elif action == "retire":
            lifecycle.retire(db, rule_id)
    except ValueError:
        pass
    return back(f"/campaigns/{campaign_id}")
