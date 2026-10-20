from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChecklistItem(Base):
    """Leadási jelölő: kampányhoz kötött, szabad szövegű, pipálható elem.
    Csak a leadási csomag teljességét jelzi, tartalmi vizsgálatot nem végez."""

    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    label: Mapped[str] = mapped_column(String(255))
    note: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(default=False)
    done_by: Mapped[int | None] = mapped_column(default=None)
    done_at: Mapped[datetime | None] = mapped_column(default=None)
