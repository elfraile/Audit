from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audits.ai.embedder import FeatureHashEmbedder
from .models import Reference


def add_reference(
    db: Session, scope_type: str, scope_id: int, name: str, category: str,
    data: bytes, filename: str, storage_dir: str = "data/references"
) -> Reference:
    target_dir = Path(storage_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{scope_type}_{scope_id}_{filename}"
    target_path.write_bytes(data)

    # Vizuális jellemzők beágyazása
    embedder = FeatureHashEmbedder()
    vector = embedder.embed_image(str(target_path))

    ref = Reference(
        scope_type=scope_type, scope_id=scope_id, name=name.strip(),
        category=category, image_path=str(target_path), embedding=vector
    )
    db.add(ref)
    db.commit()
    return ref


def list_references(db: Session, scope_type: str, scope_id: int) -> list[Reference]:
    query = select(Reference).where(
        Reference.scope_type == scope_type, Reference.scope_id == scope_id
    ).order_by(Reference.id.desc())
    return list(db.scalars(query))


def get_reference(db: Session, ref_id: int) -> Reference | None:
    return db.get(Reference, ref_id)


def delete_reference(db: Session, ref_id: int) -> None:
    ref = db.get(Reference, ref_id)
    if ref:
        p = Path(ref.image_path)
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass
        db.delete(ref)
        db.commit()
