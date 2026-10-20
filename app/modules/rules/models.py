from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base

DRAFT, APPROVED, REJECTED, RETIRED = "draft", "approved", "rejected", "retired"
STATUSES = (DRAFT, APPROVED, REJECTED, RETIRED)
SEVERITIES = ("blocking", "warning", "advice")
SCOPES = ("client", "campaign")


class Rule(Base):
    """Verziózott szabály. A `check` és `applies_to` szabad szerkezetű JSON, így a szabálytípusok
    kódváltoztatás nélkül bővíthetők."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), index=True)
    scope_id: Mapped[int] = mapped_column(index=True)
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="unclassified")
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    applies_to: Mapped[Any] = mapped_column(JSON, default=dict)
    check: Mapped[Any] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")  # pl. visszakérdezés a jóváhagyónak
    status: Mapped[str] = mapped_column(String(20), default=DRAFT, index=True)
    version: Mapped[int] = mapped_column(default=1)
    supersedes_id: Mapped[int | None] = mapped_column(default=None)
    created_by: Mapped[int | None] = mapped_column(default=None)
    approved_by: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
