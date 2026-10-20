from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base

PASSED, FAILED, WARNING = "passed", "failed", "warning"


class AuditRun(Base):
    """Egy adott asset audit futtatásának eredménye."""

    __tablename__ = "audit_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(index=True)
    asset_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(20), default=PASSED)
    passed_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    warning_count: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AuditResult(Base):
    """Egy szabály vagy tény ellenőrzésének tételes eredménye."""

    __tablename__ = "audit_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_run_id: Mapped[int] = mapped_column(index=True)
    rule_id: Mapped[int | None] = mapped_column(default=None)
    check_type: Mapped[str] = mapped_column(String(40), default="rule")
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(60), default="unclassified")
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    verdict: Mapped[str] = mapped_column(String(20), default=PASSED)
    message: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[Any] = mapped_column(JSON, default=dict)
