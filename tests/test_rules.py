import pytest

from app.modules.rules import lifecycle, queries
from app.modules.rules.extraction.null import NullExtractor
from app.modules.rules.extraction.parsing import parse_drafts
from app.modules.rules.suggest import suggest_rules
from app.modules.rules.taxonomy import DEFAULT_CATEGORIES


def test_null_extractor_splits_lines():
    drafts = NullExtractor().extract("- első szabály\n\n2) második szabály\nx", [])
    assert [d.text for d in drafts] == ["első szabály", "második szabály"]


def test_parse_drafts_tolerant():
    raw = '```json\n{"rules":[{"text":"a","category":"tone"},{"nincs":"szöveg"}]}\n```'
    drafts = parse_drafts(raw)
    assert len(drafts) == 1 and drafts[0].category == "tone"


def test_suggest_creates_drafts_with_valid_category(db):
    rules = suggest_rules(db, NullExtractor(), list(DEFAULT_CATEGORIES), "campaign", 1, "szabály egy\nszabály kettő")
    assert [r.status for r in rules] == ["draft", "draft"]
    assert {r.category for r in rules} == {"unclassified"}


def test_lifecycle_versioning(db):
    draft = lifecycle.create_draft(db, "campaign", 1, "eredeti")
    lifecycle.approve(db, draft.id)
    revised = lifecycle.edit_rule(db, draft.id, text="módosított")
    assert revised.version == 2 and revised.status == "draft"
    assert [r.text for r in queries.active_rules(db, 9, 1)] == ["eredeti"]
    lifecycle.approve(db, revised.id)
    assert [r.text for r in queries.active_rules(db, 9, 1)] == ["módosított"]


def test_active_rules_combine_scopes(db):
    for scope, sid, text in (("client", 9, "ügyfél"), ("campaign", 1, "kampány"), ("campaign", 2, "másik")):
        lifecycle.approve(db, lifecycle.create_draft(db, scope, sid, text).id)
    assert {r.text for r in queries.active_rules(db, 9, 1)} == {"ügyfél", "kampány"}


def test_invalid_changes_rejected(db):
    draft = lifecycle.create_draft(db, "campaign", 1, "x")
    with pytest.raises(ValueError):
        lifecycle.edit_rule(db, draft.id, status="approved")


def test_rule_flow_via_ui_api(admin):
    cid = admin.post("/api/clients", json={"name": "K"}).json()["id"]
    camp = admin.post(f"/api/clients/{cid}/campaigns", json={"name": "C"}).json()["id"]
    created = admin.post("/api/rules/suggest", json={"scope_type": "campaign", "scope_id": camp,
                                                      "text": "- szabály"}).json()
    assert admin.post(f"/api/rules/{created[0]['id']}/approve").json()["status"] == "approved"
    page = admin.get(f"/campaigns/{camp}")
    assert page.status_code == 200 and "szabály" in page.text
