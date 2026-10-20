from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.tenants.guards import ensure_campaign_access

from . import queries, service

router = APIRouter(prefix="/api/campaigns/{campaign_id}/facts", tags=["factsheet"])


class FactIn(BaseModel):
    key: str
    value: Any = None
    source: str = ""
    source_date: date | None = None


def _guard(db: Session, user: User, campaign_id: int) -> None:
    ensure_campaign_access(db, user, campaign_id)


def _out(f) -> dict:
    return {"id": f.id, "key": f.key, "value": f.value, "status": f.status,
            "source": f.source, "source_date": f.source_date}


@router.get("")
def list_facts(campaign_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _guard(db, user, campaign_id)
    return {"facts": [_out(f) for f in queries.confirmed_facts(db, campaign_id)],
            "open_questions": [_out(f) for f in queries.open_questions(db, campaign_id)],
            "proposals": [_out(f) for f in queries.proposals(db, campaign_id)]}


@router.post("")
def set_fact(campaign_id: int, body: FactIn, user: User = Depends(require_editor),
             db: Session = Depends(get_db)):
    _guard(db, user, campaign_id)
    fact = service.set_fact(db, campaign_id, body.key, body.value, body.source, body.source_date, user.id)
    return _out(fact)


@router.post("/questions")
def add_question(campaign_id: int, body: FactIn, user: User = Depends(require_editor),
                 db: Session = Depends(get_db)):
    _guard(db, user, campaign_id)
    try:
        return _out(service.open_question(db, campaign_id, body.key, body.source, user.id))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
