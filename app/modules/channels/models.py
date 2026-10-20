"""Anyagcsoportok (Channels) és Várt Promóciós Anyagok (Deliverables)."""
from datetime import datetime
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base


class Channel(Base):
    """Anyagcsoport / Csatorna egy kampány alatt (pl. Facebook, Újsághirdetések, POS Display)."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), default="other", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Deliverable(Base):
    """Konkrét várt promóciós anyag (slot), amihez a grafikus leadja az Assetet."""

    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(index=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))
    specs: Mapped[str] = mapped_column(String(120), default="")  # pl. 1080x1080, A4
    expected_copy: Mapped[str] = mapped_column(Text, default="")  # Képre kért kötelező szöveg
    post_copy: Mapped[str] = mapped_column(Text, default="")  # Kísérőszöveg / caption
    file_pattern: Mapped[str] = mapped_column(String(100), default="")  # pl. FB_01*, *auchan*
    asset_id: Mapped[int | None] = mapped_column(default=None, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
