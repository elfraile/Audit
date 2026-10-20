from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base

OPEN, DONE, REJECTED = "open", "done", "rejected"
STATUSES = (OPEN, DONE, REJECTED)


class Issue(Base):
    """Hibalista-tétel (kampány alatt). A hatókör (`asset_ref`) szabad szöveg: egy asset,
    több mutáció vagy a teljes kampány megnevezése."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(Text)
    asset_ref: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(60), default="unclassified")
    status: Mapped[str] = mapped_column(String(20), default=OPEN, index=True)
    promoted: Mapped[bool] = mapped_column(default=False)  # szabályjavaslat készült belőle
    created_by: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    closed_by: Mapped[int | None] = mapped_column(default=None)
    closed_at: Mapped[datetime | None] = mapped_column(default=None)


class Comment(Base):
    __tablename__ = "issue_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int | None] = mapped_column(default=None)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
