"""Modell nélküli tartalék: a szöveg sorait jelölt szabályként adja vissza, besorolás nélkül."""
import re
from collections.abc import Sequence

from app.modules.rules.schemas import RuleDraft

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


class NullExtractor:
    def extract(self, text: str, categories: Sequence[str]) -> list[RuleDraft]:
        lines = (_BULLET.sub("", raw).strip() for raw in text.splitlines())
        return [RuleDraft(text=line) for line in lines if len(line) > 3]
