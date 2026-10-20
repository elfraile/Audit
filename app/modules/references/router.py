from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.rules.access import ensure_scope_access

from . import service

router = APIRouter(prefix="/api/references", tags=["references"])


def _out(r) -> dict:
    return {
        "id": r.id, "scope_type": r.scope_type, "scope_id": r.scope_id,
        "name": r.name, "category": r.category, "created_at": r.created_at.isoformat()
    }


@router.get("")
def list_references(
    scope_type: str, scope_id: int,
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    ensure_scope_access(db, user, scope_type, scope_id)
    return [_out(r) for r in service.list_references(db, scope_type, scope_id)]


@router.post("")
async def upload_reference(
    scope_type: str = Form(...), scope_id: int = Form(...),
    name: str = Form(...), category: str = Form("logo"),
    file: UploadFile = File(...),
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_scope_access(db, user, scope_type, scope_id)
    content = await file.read()
    ref = service.add_reference(db, scope_type, scope_id, name, category, content, file.filename or "ref.png")
    return _out(ref)


@router.get("/{ref_id}/image")
def get_reference_image(ref_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ref = service.get_reference(db, ref_id)
    if not ref or not Path(ref.image_path).is_file():
        raise HTTPException(404, "Referenciakép nem található")
    ensure_scope_access(db, user, ref.scope_type, ref.scope_id)
    return FileResponse(ref.image_path)


@router.delete("/{ref_id}")
def delete_reference(ref_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)):
    ref = service.get_reference(db, ref_id)
    if not ref:
        raise HTTPException(404)
    ensure_scope_access(db, user, ref.scope_type, ref.scope_id)
    service.delete_reference(db, ref_id)
    return {"ok": True}
