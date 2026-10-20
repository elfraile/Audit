from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base

CONFIRMED = "confirmed"  # érvényes tény
PENDING = "pending"  # nyitott kérdés (még nincs érték)
PROPOSED = "proposed"  # javasolt módosítás, megerősítésre vár (sosem aktuális)


class Fact(Base):
    """Kampány-tényadat verziózva. Kampányonként és kulcsonként legfeljebb egy aktuális sor van."""

    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)  # sima egész: nincs modulfüggés
    key: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(Text, default="")
    source_date: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(20), default=CONFIRMED)
    is_current: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
