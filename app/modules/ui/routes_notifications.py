from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.notifications import service

from .deps import back, get_db, render, ui_user

router = APIRouter()


@router.get("/notifications")
def notifications_page(request: Request, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    items = service.list_for(db, user.id)
    return render(request, "notifications.html", user, items=items)


@router.post("/notifications/read")
def mark_read(user: User = Depends(ui_user), db: Session = Depends(get_db)):
    service.mark_all_read(db, user.id)
    return back("/notifications")
