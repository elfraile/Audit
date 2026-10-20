from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.modules.accounts import service

from .deps import back, get_db, render

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    return render(request, "login.html")


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = service.authenticate(db, email, password)
    if not user:
        return render(request, "login.html", error="Hibás belépési adatok")
    request.session["user_id"] = user.id
    return back("/")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return back("/login")
