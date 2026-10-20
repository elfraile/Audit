"""Ügyfél-szintű összesítő: kampányonkénti hibalista-állapot és visszatérő hibatípusok."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User
from app.modules.issues import queries
from app.modules.tenants import service as tenants

from .deps import get_db, render, ui_user

router = APIRouter()


@router.get("/clients/{client_id}")
def client_page(client_id: int, request: Request, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    client = tenants.get_client(db, client_id)
    if not client or not access.can_access(db, user, client_id):
        raise HTTPException(404)
    campaigns = tenants.campaigns_for(db, user, client_id)
    ids = [c.id for c in campaigns]
    counts = queries.status_counts(db, ids)
    recurring = queries.recurring_categories(db, ids)
    labels = request.app.state.ctx.categories.items()
    return render(request, "client.html", user, client=client, campaigns=campaigns, counts=counts,
                  recurring=recurring, labels=labels)
