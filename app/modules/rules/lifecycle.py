"""Szabályok életciklusa: javaslat -> jóváhagyás -> új verzió -> kivonás."""
from typing import Any

from sqlalchemy.orm import Session

from app.core.events import bus

from .models import APPROVED, DRAFT, REJECTED, RETIRED, SCOPES, SEVERITIES, Rule

EDITABLE = {"text", "category", "severity", "applies_to", "check", "note"}


def create_draft(db: Session, scope_type: str, scope_id: int, text: str, category: str = "unclassified",
                 severity: str = "warning", applies_to: dict | None = None, check: dict | None = None,
                 source: str = "", note: str = "", user_id: int | None = None) -> Rule:
    if scope_type not in SCOPES:
        raise ValueError(f"ismeretlen hatókör: {scope_type}")
    if severity not in SEVERITIES:
        raise ValueError(f"ismeretlen súlyosság: {severity}")
    rule = Rule(scope_type=scope_type, scope_id=scope_id, text=text.strip(), category=category,
                severity=severity, applies_to=applies_to or {}, check=check or {}, source=source,
                note=note, created_by=user_id)
    db.add(rule)
    db.commit()
    return rule


def _apply(rule: Rule, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        if field not in EDITABLE:
            raise ValueError(f"nem szerkeszthető mező: {field}")
        if field == "severity" and value not in SEVERITIES:
            raise ValueError(f"ismeretlen súlyosság: {value}")
        setattr(rule, field, value)


def edit_rule(db: Session, rule_id: int, user_id: int | None = None, **changes: Any) -> Rule:
    """Piszkozat helyben módosul; jóváhagyott szabályból új piszkozat-verzió lesz."""
    rule = db.get(Rule, rule_id)
    if not rule or rule.status not in (DRAFT, APPROVED):
        raise ValueError("a szabály nem szerkeszthető")
    if rule.status == DRAFT:
        _apply(rule, changes)
        db.commit()
        return rule
    new = Rule(scope_type=rule.scope_type, scope_id=rule.scope_id, text=rule.text, category=rule.category,
               severity=rule.severity, applies_to=rule.applies_to, check=rule.check, source=rule.source,
               note=rule.note, version=rule.version + 1, supersedes_id=rule.id, created_by=user_id)
    _apply(new, changes)
    db.add(new)
    db.commit()
    return new


def approve(db: Session, rule_id: int, user_id: int | None = None) -> Rule:
    rule = db.get(Rule, rule_id)
    if not rule or rule.status != DRAFT:
        raise ValueError("csak piszkozat hagyható jóvá")
    if rule.supersedes_id:
        old = db.get(Rule, rule.supersedes_id)
        if old:
            old.status = RETIRED
    rule.status, rule.approved_by = APPROVED, user_id
    db.commit()
    bus.publish("rule.approved", rule_id=rule.id, scope_type=rule.scope_type, scope_id=rule.scope_id)
    return rule


def reject(db: Session, rule_id: int) -> Rule:
    rule = db.get(Rule, rule_id)
    if not rule or rule.status != DRAFT:
        raise ValueError("csak piszkozat utasítható el")
    rule.status = REJECTED
    db.commit()
    return rule


def retire(db: Session, rule_id: int) -> Rule:
    rule = db.get(Rule, rule_id)
    if not rule or rule.status != APPROVED:
        raise ValueError("csak jóváhagyott szabály vonható ki")
    rule.status = RETIRED
    db.commit()
    bus.publish("rule.retired", rule_id=rule.id, scope_type=rule.scope_type, scope_id=rule.scope_id)
    return rule
