"""OpenRouter-alapú kinyerő (bármely, OpenRouteren elérhető modellel)."""
from collections.abc import Sequence

import httpx

from app.modules.rules.schemas import RuleDraft

from .parsing import parse_drafts
from .prompts import build_system_prompt

URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterExtractor:
    def __init__(self, api_key: str, model: str, timeout: float = 120.0) -> None:
        if not api_key or not model:
            raise ValueError("az OpenRouter kinyerőhöz API kulcs és modellnév kell")
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def extract(self, text: str, categories: Sequence[str]) -> list[RuleDraft]:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": build_system_prompt(categories)},
                {"role": "user", "content": text},
            ],
        }
        response = httpx.post(URL, json=payload, timeout=self.timeout,
                              headers={"Authorization": f"Bearer {self.api_key}"})
        response.raise_for_status()
        return parse_drafts(response.json()["choices"][0]["message"]["content"])
