from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from .extractor import extract_image, extract_pdf
from .models import Asset, AssetContent

SUPPORTED_EXTS = {".pdf": "pdf", ".png": "image", ".jpg": "image", ".jpeg": "image"}


def _process_file(db: Session, campaign_id: int, name: str, path: Path, prev_dir: str) -> Asset:
    ext = path.suffix.lower()
    ftype = SUPPORTED_EXTS.get(ext, "unknown")
    if ftype == "pdf":
        pages, plain_text, blocks, prev = extract_pdf(str(path), prev_dir)
    elif ftype == "image":
        pages, plain_text, blocks, prev = extract_image(str(path), prev_dir)
    else:
        pages, plain_text, blocks, prev = 1, "", [], ""

    size = path.stat().st_size if path.exists() else 0
    asset = Asset(
        campaign_id=campaign_id, name=name, file_path=str(path),
        file_type=ftype, file_size=size, page_count=pages, preview_path=prev
    )
    db.add(asset)
    db.flush()

    content = AssetContent(asset_id=asset.id, page_num=0, plain_text=plain_text, blocks=blocks)
    db.add(content)
    db.commit()
    return asset


def save_and_ingest(db: Session, campaign_id: int, filename: str, data: bytes,
                    up_dir: str = "data/uploads", prev_dir: str = "data/previews") -> Asset:
    target_dir = Path(up_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(data)
    return _process_file(db, campaign_id, filename, target_path, prev_dir)


def ingest_existing_file(db: Session, campaign_id: int, file_path: str,
                         prev_dir: str = "data/previews") -> Asset:
    p = Path(file_path)
    if not p.is_file():
        raise ValueError(f"Fájl nem található: {file_path}")
    return _process_file(db, campaign_id, p.name, p, prev_dir)


def scan_local_folder(db: Session, campaign_id: int, folder_path: str,
                      prev_dir: str = "data/previews") -> list[Asset]:
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"Mappa nem található: {folder_path}")
    created: list[Asset] = []
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTS:
            created.append(_process_file(db, campaign_id, file.name, file, prev_dir))
    return created


def get_asset(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def list_assets(db: Session, campaign_id: int) -> list[Asset]:
    return list(db.scalars(select(Asset).where(Asset.campaign_id == campaign_id).order_by(Asset.id.desc())))


def get_content(db: Session, asset_id: int, page_num: int = 0) -> AssetContent | None:
    return db.scalar(select(AssetContent).where(
        AssetContent.asset_id == asset_id, AssetContent.page_num == page_num
    ))
