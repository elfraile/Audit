from collections.abc import Sequence
from typing import Protocol

from app.modules.rules.schemas import RuleDraft


class RuleExtractor(Protocol):
    """Port: bármilyen megvalósítás (szabályalapú, lokális modell, API) ide illeszkedik."""

    def extract(self, text: str, categories: Sequence[str]) -> list[RuleDraft]: ...
