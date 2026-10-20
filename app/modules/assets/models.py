from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base


class Asset(Base):
    """Kampányhoz tartozó kreatív (PDF, kép)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(20))  # pdf, image
    file_size: Mapped[int] = mapped_column(default=0)
    page_count: Mapped[int] = mapped_column(default=1)
    preview_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AssetContent(Base):
    """Normalizált szövegréteg és blokkok pozícióval."""

    __tablename__ = "asset_contents"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(index=True)
    page_num: Mapped[int] = mapped_column(default=0)
    plain_text: Mapped[str] = mapped_column(Text, default="")
    blocks: Mapped[Any] = mapped_column(JSON, default=list)
