from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User

from . import lifecycle, queries, suggest
from .access import ensure_scope_access, ensure_rule_access
from .models import Rule

router = APIRouter(prefix="/api", tags=["rules"])


class SuggestIn(BaseModel):
    scope_type: str
    scope_id: int
    text: str
    source: str = ""


class EditIn(BaseModel):
    changes: dict


def _out(r: Rule) -> dict:
    return {"id": r.id, "scope_type": r.scope_type, "scope_id": r.scope_id, "text": r.text,
            "category": r.category, "severity": r.severity, "applies_to": r.applies_to,
            "status": r.status, "version": r.version, "note": r.note}


@router.get("/rules")
def list_rules(scope_type: str, scope_id: int, status: str | None = None,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_scope_access(db, user, scope_type, scope_id)
    return [_out(r) for r in queries.list_rules(db, scope_type, scope_id, status)]


@router.post("/rules/suggest")
def suggest_rules(body: SuggestIn, request: Request, user: User = Depends(require_editor),
                  db: Session = Depends(get_db)):
    ensure_scope_access(db, user, body.scope_type, body.scope_id)
    ctx = request.app.state.ctx
    extractor = ctx.extractors.get(ctx.settings.extractor)(ctx.settings)
    created = suggest.suggest_rules(db, extractor, ctx.categories.keys(), body.scope_type,
                                    body.scope_id, body.text, body.source, user.id)
    return [_out(r) for r in created]


def _act(db: Session, user: User, rule_id: int, action):
    ensure_rule_access(db, user, rule_id)
    try:
        return _out(action())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/rules/{rule_id}/approve")
def approve(rule_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return _act(db, user, rule_id, lambda: lifecycle.approve(db, rule_id, user.id))


@router.post("/rules/{rule_id}/reject")
def reject(rule_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return _act(db, user, rule_id, lambda: lifecycle.reject(db, rule_id))


@router.post("/rules/{rule_id}/edit")
def edit(rule_id: int, body: EditIn, user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return _act(db, user, rule_id, lambda: lifecycle.edit_rule(db, rule_id, user.id, **body.changes))
