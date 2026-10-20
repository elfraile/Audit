from app.modules.audits.ai.decision import HeuristicDecisionModel, build_abstract_decision_prompt
from app.modules.audits.engine import check_decision_rule, check_visual_reference
from app.modules.audits.models import FAILED, PASSED, WARNING


def test_abstract_decision_prompt_conformance():
    prompt = build_abstract_decision_prompt(["valid", "invalid"])
    # Ellenőrzés: nem tartalmaz konkrét példákat vagy toposzokat
    forbidden_tokens = ["e.g.", "example", "for instance", "pl.", "például"]
    for token in forbidden_tokens:
        assert token not in prompt.lower()
    assert "calibrated probability" in prompt.lower()
    assert "sum exactly to 1.0" in prompt


class MockDecisionModel:
    def __init__(self, probabilities: dict[str, float]) -> None:
        self.probabilities = probabilities

    def evaluate(self, image_path: str, context_text: str, question: str, options: list[str]) -> dict[str, float]:
        return self.probabilities


def test_check_decision_rule():
    # 1. Sikeres döntési kimenet
    m_pass = MockDecisionModel({"yes": 0.92, "no": 0.08})
    v1, _, ev1 = check_decision_rule(
        "A hangnem magázó?", "yes", ["yes", "no"], "", "Szöveg", min_prob=0.75, decision_model=m_pass
    )
    assert v1 == PASSED
    assert ev1["selected"] == "yes"

    # 2. Eltérést jelző kimenet
    m_fail = MockDecisionModel({"yes": 0.10, "no": 0.90})
    v2, _, ev2 = check_decision_rule(
        "A hangnem magázó?", "yes", ["yes", "no"], "", "Szöveg", min_prob=0.75, decision_model=m_fail
    )
    assert v2 == FAILED
    assert ev2["selected"] == "no"

    # 3. Bizonytalan kimenet (alacsony bizonyosság)
    m_warn = MockDecisionModel({"yes": 0.52, "no": 0.48})
    v3, _, ev3 = check_decision_rule(
        "A hangnem magázó?", "yes", ["yes", "no"], "", "Szöveg", min_prob=0.75, decision_model=m_warn
    )
    assert v3 == WARNING


def test_check_visual_reference(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"dummy")
    
    # 1. Magas hasonlóság
    class HighSimEmbedder:
        def embed_image(self, path): return [1.0, 0.0]
    
    v_pass, _, ev_pass = check_visual_reference(
        [1.0, 0.0], str(p), min_similarity=0.8, embedder=HighSimEmbedder()
    )
    assert v_pass == PASSED
    assert ev_pass["similarity"] == 1.0

    # 2. Alacsony hasonlóság
    class LowSimEmbedder:
        def embed_image(self, path): return [0.0, 1.0]

    v_fail, _, ev_fail = check_visual_reference(
        [1.0, 0.0], str(p), min_similarity=0.8, embedder=LowSimEmbedder()
    )
    assert v_fail == FAILED
    assert ev_fail["similarity"] == 0.0
