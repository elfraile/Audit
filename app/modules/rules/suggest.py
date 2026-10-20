"""Szabály-kinyerő: szövegből szabályjelöltek. A megvalósítás cserélhető (lásd extraction/)."""
from collections.abc import Sequence

from sqlalchemy.orm import Session

from . import lifecycle
from .extraction.port import RuleExtractor
from .models import SEVERITIES, Rule


def suggest_rules(db: Session, extractor: RuleExtractor, categories: Sequence[str], scope_type: str,
                  scope_id: int, text: str, source: str = "", user_id: int | None = None,
                  applies_to: dict | None = None) -> list[Rule]:
    created = []
    for draft in extractor.extract(text, categories):
        severity = draft.severity if draft.severity in SEVERITIES else "warning"
        category = draft.category if draft.category in categories else "unclassified"
        merged_applies = dict(draft.applies_to or {})
        if applies_to:
            merged_applies.update(applies_to)
        created.append(lifecycle.create_draft(
            db, scope_type, scope_id, draft.text, category, severity, merged_applies,
            source=source or text[:200], note=draft.question, user_id=user_id))
    return created
