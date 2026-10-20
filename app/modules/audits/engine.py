import re
from typing import Any

from app.modules.audits.ai.decision import DecisionModel, HeuristicDecisionModel
from app.modules.audits.ai.embedder import FeatureHashEmbedder, MultimodalEmbedder, cosine_similarity
from .matcher import extract_quotes, find_in_blocks, normalize_text
from .models import FAILED, PASSED, WARNING


def check_visual_reference(
    ref_embedding: list[float], asset_preview_path: str, min_similarity: float = 0.70,
    embedder: MultimodalEmbedder | None = None
) -> tuple[str, str, dict]:
    if not ref_embedding or not asset_preview_path:
        return WARNING, "Hiányzó vizuális referencia vagy előnézeti kép", {}

    emb = embedder or FeatureHashEmbedder()
    asset_vector = emb.embed_image(asset_preview_path)
    sim = cosine_similarity(ref_embedding, asset_vector)

    ev = {"similarity": round(sim, 3), "min_similarity": min_similarity}
    if sim >= min_similarity:
        return PASSED, f"Vizuális referencia azonosítva (hasonlóság: {sim:.2f} >= {min_similarity})", ev
    return FAILED, f"A vizuális referencia nem azonosítható biztonsággal (hasonlóság: {sim:.2f} < {min_similarity})", ev


def check_decision_rule(
    question: str, expected_option: str, options: list[str],
    image_path: str, text: str, min_prob: float = 0.75,
    decision_model: DecisionModel | None = None
) -> tuple[str, str, dict]:
    model = decision_model or HeuristicDecisionModel()
    probs = model.evaluate(image_path, text, question, options)
    best_opt = max(probs, key=probs.get) if probs else ""
    best_prob = probs.get(best_opt, 0.0)

    ev = {"question": question, "probabilities": probs, "selected": best_opt, "expected": expected_option}
    if best_prob < min_prob:
        return WARNING, f"Bizonytalan döntési kimenet (legjobb valószínűség: {best_prob:.2f} < {min_prob})", ev

    if best_opt == expected_option:
        return PASSED, f"Döntési modell igazolta az elvárást ({best_opt}: {best_prob:.2f})", ev
    return FAILED, f"Döntési modell eltérést jelzett ({best_opt} != {expected_option})", ev


def check_rule(
    rule_text: str, check_spec: dict, full_text: str, blocks: list[dict],
    asset_preview_path: str = "", ref_resolver: Any = None,
    decision_model: DecisionModel | None = None
) -> tuple[str, str, dict]:
    norm_full = normalize_text(full_text).lower()

    # 1. Tiltott minta ellenőrzése
    forbidden = check_spec.get("forbidden") or (check_spec.get("text") if check_spec.get("type") == "forbidden" else None)
    if forbidden:
        found = find_in_blocks(forbidden, blocks)
        if found or (normalize_text(forbidden).lower() in norm_full):
            return FAILED, f"Tiltott elem található az anyagban: '{forbidden}'", found or {"text": forbidden}
        return PASSED, f"Tiltott elem nem található: '{forbidden}'", {}

    # 2. Kötelező minta ellenőrzése
    must_contain = check_spec.get("must_contain") or (check_spec.get("text") if check_spec.get("type") == "must_contain" else None)
    if must_contain:
        found = find_in_blocks(must_contain, blocks)
        if not found and (normalize_text(must_contain).lower() not in norm_full):
            return FAILED, f"Hiányzó kötelező tartalom: '{must_contain}'", {"expected": must_contain}
        return PASSED, f"Megtalálva: '{must_contain}'", found or {"text": must_contain}

    # 3. Vizuális referencia ellenőrzése (ha a szabályhoz referencia van kötve)
    ref_id = check_spec.get("visual_ref_id")
    if ref_id and ref_resolver:
        ref = ref_resolver(ref_id)
        if ref and ref.embedding:
            min_sim = check_spec.get("min_similarity", 0.70)
            return check_visual_reference(ref.embedding, asset_preview_path, min_sim)

    # 4. Döntési modell kérdés (ha definiálva van)
    dec_question = check_spec.get("decision_question")
    if dec_question:
        opts = check_spec.get("options", ["yes", "no"])
        expected = check_spec.get("expected", "yes")
        min_p = check_spec.get("min_prob", 0.75)
        return check_decision_rule(dec_question, expected, opts, asset_preview_path, full_text, min_p, decision_model)

    # 5. Regex vizsgálat
    regex_pattern = check_spec.get("regex") or (check_spec.get("pattern") if check_spec.get("type") == "regex" else None)
    if regex_pattern:
        m = re.search(regex_pattern, full_text, re.IGNORECASE)
        if not m:
            return FAILED, f"A megadott minta nem illeszkedik ({regex_pattern})", {"pattern": regex_pattern}
        return PASSED, f"Minta illeszkedik ({m.group(0)})", {"matched": m.group(0)}

    # 6. Automatikus idézőjel-vizsgálat szabályszövegből
    quotes = extract_quotes(rule_text)
    if quotes:
        for q in quotes:
            found = find_in_blocks(q, blocks)
            if not found and (normalize_text(q).lower() not in norm_full):
                return FAILED, f"A megadott kifejezés hiányzik: '{q}'", {"expected": q}
        return PASSED, f"Minden hivatkozott kifejezés megtalálható ({', '.join(quotes)})", {}

    # 7. Nem determinisztikus vagy általános szabály
    return WARNING, "A szabály emberi vagy szemantikai felülvizsgálatot igényel", {}


def check_fact(key: str, val: Any, full_text: str, blocks: list[dict]) -> tuple[str, str, dict] | None:
    if not isinstance(val, str) or len(val.strip()) < 3:
        return None
    val_clean = val.strip()
    found = find_in_blocks(val_clean, blocks)
    norm_full = normalize_text(full_text).lower()
    if found or (normalize_text(val_clean).lower() in norm_full):
        return PASSED, f"Kampány-adat ({key}) igazolva az anyagon: '{val_clean}'", found or {"value": val_clean}
    return FAILED, f"A kampány-adat ({key}) nem szerepel a kreatívon: '{val_clean}'", {"expected": val_clean}
