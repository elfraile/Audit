"""Feliratkozások az issues modul eseményeire (az issues modult nem importálja)."""
from app.modules.accounts import access

from . import service
from .mentions import find_mentions


def _link(issue) -> str:
    return f"/issues/{issue.id}"


def _short(text: str, n: int = 80) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _notify_all(db, issue, client_id, actor_id, kind, text, mentioned=frozenset()) -> None:
    for user in access.recipients(db, client_id, issue.campaign_id, actor_id):
        label, k = (f"Megemlítettek: {text}", "mention") if user.id in mentioned else (text, kind)
        service.add(db, user.id, k, label, _link(issue))
    db.commit()


def on_created(db, issue, client_id, actor_id, **_) -> None:
    _notify_all(db, issue, client_id, actor_id, "issue_new", f"Új hibalista-tétel: {_short(issue.description)}")


def on_status(db, issue, client_id, actor_id, **_) -> None:
    _notify_all(db, issue, client_id, actor_id, "issue_status",
                f"Állapotváltozás ({issue.status}): {_short(issue.description)}")


def on_commented(db, issue, client_id, actor_id, comment, **_) -> None:
    _notify_all(db, issue, client_id, actor_id, "comment", f"Új megjegyzés: {_short(comment.body)}",
                mentioned=find_mentions(db, comment.body))


def subscribe(bus) -> None:
    bus.subscribe("issue.created", on_created)
    bus.subscribe("issue.status_changed", on_status)
    bus.subscribe("issue.commented", on_commented)
