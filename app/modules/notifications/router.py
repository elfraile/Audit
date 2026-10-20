from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user
from app.modules.accounts.models import User

from . import service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"unread": service.unread_count(db, user.id),
            "items": [{"id": n.id, "kind": n.kind, "text": n.text, "link": n.link, "read": n.is_read}
                      for n in service.list_for(db, user.id)]}


@router.post("/read")
def mark_read(user: User = Depends(current_user), db: Session = Depends(get_db)):
    service.mark_all_read(db, user.id)
    return {"ok": True}
