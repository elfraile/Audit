"""@megjelölések felismerése: @<e-mail előtag> egyezik a felhasználó e-mail címének helyi részével."""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounts.models import User

_TOKEN = re.compile(r"@([\w.\-]+)")


def find_mentions(db: Session, body: str) -> set[int]:
    tokens = {t.lower() for t in _TOKEN.findall(body)}
    if not tokens:
        return set()
    users = db.scalars(select(User).where(User.is_active.is_(True)))
    return {u.id for u in users if u.email.split("@")[0].lower() in tokens}
