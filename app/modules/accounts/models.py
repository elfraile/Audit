from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(default=True)


class Grant(Base):
    """Hozzáférés egy ügyfélhez (campaign_id üres) vagy egyetlen kampányához.

    A client_id/campaign_id szándékosan sima egész szám (nem FK): az accounts modul
    így nem függ a tenants modultól.
    """

    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(index=True)
    campaign_id: Mapped[int | None] = mapped_column(default=None)
