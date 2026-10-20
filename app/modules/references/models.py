from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base


class Reference(Base):
    """Jóváhagyott márkaelem vagy termék referencia-kép (pl. hivatalos logó, csomagolás)."""

    __tablename__ = "references"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), index=True)  # client vagy campaign
    scope_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(60), default="logo")  # logo, product, pack, other
    image_path: Mapped[str] = mapped_column(String(500))
    embedding: Mapped[Any] = mapped_column(JSON, default=list)  # multimodális vektor (pl. 768d)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
