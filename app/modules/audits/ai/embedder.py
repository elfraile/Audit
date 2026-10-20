import math
from pathlib import Path
from typing import Protocol
import httpx
from PIL import Image


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class MultimodalEmbedder(Protocol):
    def embed_image(self, image_path: str) -> list[float]: ...
    def embed_text(self, text: str) -> list[float]: ...


class FeatureHashEmbedder:
    """Gyors, helyi képjellemző-kinyerő a vizuális hasonlósághoz (PIL alapú)."""

    def embed_image(self, image_path: str) -> list[float]:
        p = Path(image_path)
        if not p.is_file():
            return [0.0] * 64
        with Image.open(p) as img:
            rgb = img.convert("RGB").resize((8, 8))
            pixels = list(rgb.getdata())
            # 64 dimenziós normalizált szürkeárnyalatos profil
            grays = [(r * 0.299 + g * 0.587 + b * 0.114) for r, g, b in pixels]
            norm = math.sqrt(sum(g * g for g in grays)) or 1.0
            return [g / norm for g in grays]

    def embed_text(self, text: str) -> list[float]:
        # Szöveges profil azonos dimenzióra
        words = text.lower().split()
        vec = [0.0] * 64
        for i, w in enumerate(words):
            vec[hash(w) % 64] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class LlamaServerEmbedder:
    """Helyi llama-server (/v1/embeddings) kompatibilis beágyazó."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8080/v1/embeddings") -> None:
        self.endpoint = endpoint

    def embed_image(self, image_path: str) -> list[float]:
        # Képútvonal továbbítása vagy helyi kinyerés
        return FeatureHashEmbedder().embed_image(image_path)

    def embed_text(self, text: str) -> list[float]:
        try:
            resp = httpx.post(self.endpoint, json={"input": text}, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except Exception:
            pass
        return FeatureHashEmbedder().embed_text(text)
