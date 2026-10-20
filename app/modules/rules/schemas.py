from typing import Any

from pydantic import BaseModel, Field


class RuleDraft(BaseModel):
    """A kinyerők közös kimeneti formátuma (a modell/megvalósítás cserélhető mögötte)."""

    text: str
    category: str = "unclassified"
    severity: str = "warning"
    applies_to: dict[str, Any] = Field(default_factory=dict)
    question: str = ""  # nem egyértelmű pont: visszakérdezés az asszisztensnek
