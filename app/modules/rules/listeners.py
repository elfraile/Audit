"""A szabálymodul feliratkozásai más modulok eseményeire."""
from . import lifecycle

# Az issues modul eseménye; szöveges név, hogy ne legyen importfüggés.
RULE_REQUESTED = "issue.rule_requested"


def on_rule_requested(db, issue, client_id, actor_id, scope_type, **_) -> None:
    """Hibalista-tételből szabály-piszkozat (jóváhagyásra vár)."""
    scope_id = client_id if scope_type == "client" else issue.campaign_id
    lifecycle.create_draft(db, scope_type, scope_id, issue.description, issue.category,
                           source=f"Hibalista #{issue.id}", user_id=actor_id)


def subscribe(bus) -> None:
    bus.subscribe(RULE_REQUESTED, on_rule_requested)
