import re
from typing import Any


def normalize_text(text: str) -> str:
    """Sortörések és több szóköz egységesítése."""
    return " ".join(text.split()).strip()


def find_in_blocks(needle: str, blocks: list[dict], case_sensitive: bool = False) -> dict[str, Any] | None:
    """Keresett szöveg vagy kifejezés megkeresése a pozícionált blokkokban."""
    norm_needle = normalize_text(needle)
    if not norm_needle:
        return None

    target = norm_needle if case_sensitive else norm_needle.lower()
    for b in blocks:
        block_text = normalize_text(b.get("text", ""))
        curr = block_text if case_sensitive else block_text.lower()
        if target in curr:
            return {
                "page": b.get("page", 0),
                "bbox": b.get("bbox", []),
                "matched_text": b.get("text", "")
            }
    return None


def extract_quotes(text: str) -> list[str]:
    """Idézőjeles kifejezések kinyerése a szabály szövegéből."""
    pattern = r'["„\']([^"”\']+)["”\']'
    matches = re.findall(pattern, text)
    return [m.strip() for m in matches if len(m.strip()) > 2]
