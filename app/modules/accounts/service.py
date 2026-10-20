from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password

from .models import Grant, User
from .roles import ADMIN, ROLES


def create_user(db: Session, email: str, name: str, password: str, role: str = "viewer") -> User:
    if role not in ROLES:
        raise ValueError(f"ismeretlen szerepkör: {role}")
    user = User(email=email.strip().lower(), name=name, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user and user.is_active and verify_password(password, user.password_hash):
        return user
    return None


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def user_names(db: Session, ids: set[int]) -> dict[int, str]:
    return {u.id: u.name for u in db.scalars(select(User).where(User.id.in_(ids)))}


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.email)))


def ensure_admin(db: Session, email: str, password: str) -> None:
    if not db.scalar(select(User).where(User.role == ADMIN)):
        create_user(db, email, "Admin", password, ADMIN)
