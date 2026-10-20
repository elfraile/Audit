"""A modell JSON-válaszának hibatűrő feldolgozása."""
import json
import re

from pydantic import ValidationError

from app.modules.rules.schemas import RuleDraft

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def parse_drafts(content: str) -> list[RuleDraft]:
    data = json.loads(_FENCE.sub("", content.strip()))
    items = data.get("rules", []) if isinstance(data, dict) else data
    drafts = []
    for item in items:
        try:
            drafts.append(RuleDraft.model_validate(item))
        except ValidationError:
            continue
    return drafts
