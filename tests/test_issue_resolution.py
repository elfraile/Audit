import pytest
from app.modules.accounts import service as accounts, access
from app.modules.assets.models import Asset, AssetContent
from app.modules.audits import service as audit_service
from app.modules.audits.models import FAILED, PASSED
from app.modules.checklist import service as checklist_service
from app.modules.issues import queries as issue_queries, service as issue_service
from app.modules.issues.models import DONE, OPEN
from app.modules.issues.resolver import check_delivery_readiness, resolve_issues_for_audit
from app.modules.rules import lifecycle as rule_lifecycle
from app.modules.tenants import service as tenants


@pytest.fixture()
def setup_campaign(db):
    client = tenants.create_client(db, "Teszt Ügyfél")
    campaign = tenants.create_campaign(db, client.id, "Teszt Kampány")
    user = accounts.create_user(db, "auditor@test.local", "Auditor", "pass", "editor")
    access.grant_access(db, user.id, client.id)

    # Asset létrehozása
    asset = Asset(
        campaign_id=campaign.id, name="teszt_kreativ.pdf",
        file_path="teszt_kreativ.pdf", file_type="pdf", file_size=1024,
        page_count=1, preview_path=""
    )
    db.add(asset)
    db.flush()

    content = AssetContent(
        asset_id=asset.id, page_num=0,
        plain_text="Kóstolja meg a prémium terméket! 2026. november 15-ig.",
        blocks=[]
    )
    db.add(content)
    db.commit()

    return client, campaign, user, asset


def test_auto_resolution_when_asset_audit_passes(db, setup_campaign):
    client, campaign, user, asset = setup_campaign

    # Nyitott hiba felvitele az adott kreatívra
    issue = issue_service.create_issue(
        db, campaign.id, description="Szöveghiba javítandó a kreatívon",
        asset_ref=asset.name, category="copy", user_id=user.id, asset_id=asset.id
    )
    assert issue.status == OPEN

    # Szabály hozzáadása, ami teljesül a szövegben
    rule = rule_lifecycle.create_draft(
        db, scope_type="campaign", scope_id=campaign.id,
        text="A prémium szónak szerepelnie kell", category="copy",
        check={"type": "must_contain", "text": "prémium"}
    )
    rule_lifecycle.approve(db, rule.id, user.id)

    # Audit futtatása: mivel a szöveg tartalmazza a 'prémium' szót, a szabály PASSED
    run = audit_service.run_audit(db, campaign.id, asset.id, user_id=user.id)
    assert run.status == PASSED

    # Ellenőrizzük, hogy a hiba automatikusan lezárult
    db.refresh(issue)
    assert issue.status == DONE
    assert issue.closed_by == user.id

    # Ellenőrizzük az audit lezáró megjegyzést
    comments = issue_queries.comments(db, issue.id)
    assert any("Automatikus feloldás" in c.body for c in comments)


def test_auto_resolution_specific_rule(db, setup_campaign):
    client, campaign, user, asset = setup_campaign

    # Szabály létrehozása
    rule = rule_lifecycle.create_draft(
        db, scope_type="campaign", scope_id=campaign.id,
        text="Kötelező dátum", category="legal",
        check={"type": "must_contain", "text": "2026"}
    )
    rule_lifecycle.approve(db, rule.id, user.id)

    # Hiba tétel konkrét rule_id-val
    issue = issue_service.create_issue(
        db, campaign.id, description="Dátum formátum javítás",
        asset_ref=asset.name, category="legal", user_id=user.id,
        asset_id=asset.id, rule_id=rule.id
    )
    assert issue.status == OPEN

    # Audit futtatása
    audit_service.run_audit(db, campaign.id, asset.id, user_id=user.id)

    db.refresh(issue)
    assert issue.status == DONE


def test_delivery_readiness_lifecycle(db, setup_campaign):
    client, campaign, user, asset = setup_campaign

    # Kezdetben nincs leauditálva az asset
    status1 = check_delivery_readiness(db, campaign.id)
    assert status1["ready"] is False
    assert status1["audited_assets"] == 0

    # Sikeres audit után sincs még kész, ha van nyitott checklist vagy hiba
    item = checklist_service.add_item(db, campaign.id, "Végleges méretellenőrzés")
    issue = issue_service.create_issue(db, campaign.id, "Képi korrekció", asset_ref="egyeb.png")

    audit_service.run_audit(db, campaign.id, asset.id, user_id=user.id)
    status2 = check_delivery_readiness(db, campaign.id)
    assert status2["ready"] is False
    assert status2["open_issues"] == 1
    assert status2["pending_checklist"] == 1

    # Hiba lezárása és checklist kipipálása
    issue_service.set_status(db, issue.id, DONE, user_id=user.id)
    checklist_service.set_done(db, item.id, True, user_id=user.id)

    # Most már minden feltétel zöld
    status3 = check_delivery_readiness(db, campaign.id)
    assert status3["ready"] is True
    assert status3["open_issues"] == 0
    assert status3["pending_checklist"] == 0
    assert "Minden kreatív anyag sikeresen auditálva" in status3["reasons"][0]
