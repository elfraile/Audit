"""Egyetlen helyen kezelt időbélyeg (UTC, időzóna nélkül tárolva)."""
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
