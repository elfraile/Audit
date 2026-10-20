import pytest

from app.modules.factsheet import queries, service


def test_set_fact_supersedes_previous(db):
    service.set_fact(db, 1, "k", "a")
    service.set_fact(db, 1, "k", "b")
    assert queries.as_mapping(db, 1) == {"k": "b"}
    assert [f.value for f in queries.history(db, 1, "k")] == ["a", "b"]


def test_open_question_then_answer(db):
    service.open_question(db, 1, "k", "kérdés")
    assert [f.key for f in queries.open_questions(db, 1)] == ["k"]
    service.set_fact(db, 1, "k", "v")
    assert queries.open_questions(db, 1) == []


def test_proposal_does_not_override_until_accepted(db):
    service.set_fact(db, 1, "k", "old")
    proposal = service.propose_change(db, 1, "k", "new")
    assert queries.as_mapping(db, 1) == {"k": "old"}
    service.accept_proposal(db, proposal.id)
    assert queries.as_mapping(db, 1) == {"k": "new"}


def test_open_question_cannot_replace_existing(db):
    service.set_fact(db, 1, "k", "v")
    with pytest.raises(ValueError):
        service.open_question(db, 1, "k")


def test_fact_event_published(db):
    from app.core.events import bus

    seen = []
    bus.subscribe("fact.changed", lambda **kw: seen.append(kw["key"]))
    service.set_fact(db, 7, "evt", "1")
    assert "evt" in seen
