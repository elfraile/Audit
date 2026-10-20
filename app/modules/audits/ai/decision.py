import json
import re
from typing import Protocol
import httpx


class DecisionModel(Protocol):
    def evaluate(self, image_path: str, context_text: str, question: str, options: list[str]) -> dict[str, float]:
        """Kérdés kiértékelése és kalibrált valószínűségek visszaadása a megadott opciókra."""
        ...


def build_abstract_decision_prompt(options: list[str]) -> str:
    """Tiszta, absztrakt strukturális döntési rendszerprompt, konkrét példák nélkül."""
    opts = ", ".join(f'"{o}"' for o in options)
    return (
        "You are a multimodal decision evaluator operating on structured state.\n"
        "Instructions:\n"
        "1. Assess the provided multimodal state strictly with respect to the specified inquiry.\n"
        "2. Do not generate explanations, reasoning, or conversational prose.\n"
        f"3. Return calibrated probability scores between 0.0 and 1.0 for each option in [{opts}].\n"
        "4. The probabilities across all specified options must sum exactly to 1.0.\n"
        "Output a single JSON object mapping each option to its probability score. Output nothing else."
    )


class OpenRouterDecisionModel:
    """OpenRouter vagy Cloudflare alapú döntési modell (pl. Clef család)."""

    def __init__(self, api_key: str, model: str = "@cf/cloudflare/clef-omni", timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def evaluate(self, image_path: str, context_text: str, question: str, options: list[str]) -> dict[str, float]:
        if not self.api_key:
            return HeuristicDecisionModel().evaluate(image_path, context_text, question, options)

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        prompt = build_abstract_decision_prompt(options)
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Context:\n{context_text}\n\nInquiry: {question}"}
            ]
        }
        try:
            resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip()))
                probs = {opt: float(data.get(opt, 0.0)) for opt in options}
                total = sum(probs.values()) or 1.0
                return {k: round(v / total, 3) for k, v in probs.items()}
        except Exception:
            pass
        return HeuristicDecisionModel().evaluate(image_path, context_text, question, options)


class HeuristicDecisionModel:
    """Gyors offline döntési modell teszteléshez és fallback működéshez."""

    def evaluate(self, image_path: str, context_text: str, question: str, options: list[str]) -> dict[str, float]:
        if not options:
            return {}
        # Alapértelmezett egyenletes eloszlás bizonytalanság esetén
        prob = round(1.0 / len(options), 3)
        return {opt: prob for opt in options}
