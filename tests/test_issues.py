import pytest

from app.modules.accounts import access, service as accounts
from app.modules.issues import queries, service
from app.modules.notifications import service as notes
from app.modules.checklist import service as checklist
from app.modules.rules import queries as rule_queries
from app.modules.tenants import service as tenants


@pytest.fixture()
def setup(db):
    client = tenants.create_client(db, "K")
    campaign = tenants.create_campaign(db, client.id, "C")
    author = accounts.create_user(db, "author@t.local", "Author", "x", "editor")
    other = accounts.create_user(db, "other@t.local", "Other", "x", "editor")
    outsider = accounts.create_user(db, "out@t.local", "Out", "x", "editor")
    for user in (author, other):
        access.grant_access(db, user.id, client.id)
    return client, campaign, author, other, outsider


def test_issue_lifecycle_and_counts(db, setup):
    _, campaign, author, *_ = setup
    issue = service.create_issue(db, campaign.id, "javítandó", category="tone", user_id=author.id)
    assert [i.id for i in queries.open_issues(db, campaign.id)] == [issue.id]
    service.set_status(db, issue.id, "done", author.id)
    assert queries.open_issues(db, campaign.id) == [] and queries.closed_issues(db, campaign.id)[0].closed_by == author.id
    service.set_status(db, issue.id, "open", author.id)
    assert queries.status_counts(db, [campaign.id])[campaign.id]["open"] == 1
    assert queries.recurring_categories(db, [campaign.id]) == [("tone", 1)]


def test_validation(db, setup):
    _, campaign, *_ = setup
    with pytest.raises(ValueError):
        service.create_issue(db, campaign.id, "  ")
    issue = service.create_issue(db, campaign.id, "x")
    with pytest.raises(ValueError):
        service.set_status(db, issue.id, "bogus")


def test_notifications_only_for_authorized_others(db, setup):
    _, campaign, author, other, outsider = setup
    issue = service.create_issue(db, campaign.id, "új hiba", user_id=author.id)
    assert notes.unread_count(db, other.id) == 1
    assert notes.unread_count(db, author.id) == 0  # a szerző nem kap értesítést
    assert notes.unread_count(db, outsider.id) == 0  # hozzáférés nélkül sem
    service.add_comment(db, issue.id, "nézd meg @other", author.id)
    kinds = [n.kind for n in notes.list_for(db, other.id)]
    assert "mention" in kinds
    notes.mark_all_read(db, other.id)
    assert notes.unread_count(db, other.id) == 0


def test_promote_creates_rule_draft_once(db, setup):
    client, campaign, author, *_ = setup
    issue = service.create_issue(db, campaign.id, "állandó elvárás", category="terminology", user_id=author.id)
    service.request_rule(db, issue.id, "client", author.id)
    drafts = rule_queries.drafts(db, "client", client.id)
    assert len(drafts) == 1 and drafts[0].category == "terminology"
    with pytest.raises(ValueError):
        service.request_rule(db, issue.id, "client", author.id)


def test_checklist(db, setup):
    _, campaign, author, *_ = setup
    item = checklist.add_item(db, campaign.id, "leadási elvárás")
    checklist.set_done(db, item.id, True, author.id)
    assert checklist.list_items(db, campaign.id)[0].done is True
    checklist.set_done(db, item.id, False)
    assert checklist.list_items(db, campaign.id)[0].done_by is None


def test_pages_and_api(admin):
    cid = admin.post("/api/clients", json={"name": "K"}).json()["id"]
    camp = admin.post(f"/api/clients/{cid}/campaigns", json={"name": "C"}).json()["id"]
    issue = admin.post(f"/api/campaigns/{camp}/issues", json={"description": "tétel"}).json()
    admin.post(f"/api/issues/{issue['id']}/comments", json={"body": "megjegyzés"})
    admin.post(f"/api/campaigns/{camp}/checklist", json={"label": "jelölő"})
    for url in (f"/campaigns/{camp}", f"/issues/{issue['id']}", f"/clients/{cid}", "/notifications"):
        assert admin.get(url).status_code == 200, url
    assert admin.get(f"/api/campaigns/{camp}/checklist").json()[0]["label"] == "jelölő"
    assert admin.post(f"/api/issues/{issue['id']}/promote", json={"scope_type": "campaign"}).json()["promoted"]
