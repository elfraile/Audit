import pytest
from app.modules.accounts import service as accounts, access
from app.modules.assets.models import Asset, AssetContent
from app.modules.audits import service as audit_service
from app.modules.audits.models import FAILED, PASSED
from app.modules.channels import service as channel_service
from app.modules.issues.resolver import check_delivery_readiness
from app.modules.rules import lifecycle as rule_lifecycle
from app.modules.tenants import service as tenants


@pytest.fixture()
def setup_campaign_channels(db):
    client = tenants.create_client(db, "Podravka")
    campaign = tenants.create_campaign(db, client.id, "Auchan TM Promóció")
    user = accounts.create_user(db, "pm@agency.local", "PM", "pass", "editor")
    access.grant_access(db, user.id, client.id)

    # 1. Két különböző anyagcsoport létrehozása
    ch_social = channel_service.create_channel(
        db, campaign.id, name="Facebook / Social", code="social",
        description="Social media feed posztok"
    )
    ch_pos = channel_service.create_channel(
        db, campaign.id, name="POS Display", code="pos",
        description="Bolti display és nyomtatott anyagok"
    )

    # 2. Várt promóciós anyagok (Deliverables) rögzítése
    deliv_fb1 = channel_service.create_deliverable(
        db, channel_id=ch_social.id, campaign_id=campaign.id,
        name="FB Poszt #1 (Bejelentő)", specs="1080x1080",
        expected_copy="Vásárolj 2 db terméket és nyerj!",
        post_copy="Indul az őszi promóció! Játékszabályzat a bioban.",
        file_pattern="FB_01*"
    )

    deliv_pos1 = channel_service.create_deliverable(
        db, channel_id=ch_pos.id, campaign_id=campaign.id,
        name="Hullámkarton display", specs="Raklapos palást",
        expected_copy="Keresd a kiemelt kihelyezést!",
        file_pattern="*display*"
    )

    return client, campaign, user, ch_social, ch_pos, deliv_fb1, deliv_pos1


def test_channel_deliverables_and_auto_match(db, setup_campaign_channels):
    client, campaign, user, ch_social, ch_pos, deliv_fb1, deliv_pos1 = setup_campaign_channels

    # Csoportok és tételek listázása
    channels = channel_service.list_channels(db, campaign.id)
    assert len(channels) == 2
    assert {c.code for c in channels} == {"social", "pos"}

    delivs = channel_service.list_deliverables(db, campaign.id, channel_id=ch_social.id)
    assert len(delivs) == 1
    assert delivs[0].name == "FB Poszt #1 (Bejelentő)"
    assert delivs[0].asset_id is None

    # Még nincs leadva az anyag -> Delivery readiness jelzi a hiányt
    readiness1 = check_delivery_readiness(db, campaign.id)
    assert readiness1["ready"] is False
    assert readiness1["missing_deliverables"] == 2

    # Feltöltésre kerül a kreatív a megadott mintájú névvel
    fb_asset = Asset(
        campaign_id=campaign.id, name="FB_01_Auchan_Feed_v1.png",
        file_path="FB_01_Auchan_Feed_v1.png", file_type="image", file_size=2048,
        page_count=1, preview_path=""
    )
    db.add(fb_asset)
    db.commit()

    # Automatikus párosítás lefutása
    matched = channel_service.auto_match_deliverables(db, campaign.id)
    assert matched == 1

    db.refresh(deliv_fb1)
    db.refresh(fb_asset)
    assert deliv_fb1.asset_id == fb_asset.id
    assert fb_asset.deliverable_id == deliv_fb1.id
    assert fb_asset.channel_id == ch_social.id


def test_channel_specific_rules_and_copy_check(db, setup_campaign_channels):
    client, campaign, user, ch_social, ch_pos, deliv_fb1, deliv_pos1 = setup_campaign_channels

    # 1. Globális ügyfélszabály (mindenre érvényes)
    rule_global = rule_lifecycle.create_draft(
        db, scope_type="client", scope_id=client.id,
        text="A Podravka névnek szerepelnie kell", category="brand",
        check={"type": "must_contain", "text": "Podravka"}
    )
    rule_lifecycle.approve(db, rule_global.id, user.id)

    # 2. Csatorna-specifikus szabály: CSAK a Facebook csoportra
    rule_social = rule_lifecycle.create_draft(
        db, scope_type="channel", scope_id=ch_social.id,
        text="A bioban szó kötelező a social szövegezésben", category="copy",
        check={"type": "must_contain", "text": "bioban"}
    )
    rule_lifecycle.approve(db, rule_social.id, user.id)

    # 3. Csatorna-specifikus szabály: CSAK a POS csoportra
    rule_pos = rule_lifecycle.create_draft(
        db, scope_type="channel", scope_id=ch_pos.id,
        text="A raklap szó kötelező a POS displayen", category="layout",
        check={"type": "must_contain", "text": "raklap"}
    )
    rule_lifecycle.approve(db, rule_pos.id, user.id)

    # Asset létrehozása a Facebook poszthoz, benne a kért szövegekkel
    fb_asset = Asset(
        campaign_id=campaign.id, name="FB_01_Feed.png",
        file_path="FB_01_Feed.png", file_type="image", file_size=1024,
        page_count=1, preview_path="", channel_id=ch_social.id, deliverable_id=deliv_fb1.id
    )
    db.add(fb_asset)
    db.flush()

    content = AssetContent(
        asset_id=fb_asset.id, page_num=0,
        plain_text="Podravka promóció! Vásárolj 2 db terméket és nyerj! Részletek a bioban.",
        blocks=[]
    )
    db.add(content)
    db.commit()

    # Audit futtatása a Facebook anyagra
    run = audit_service.run_audit(db, campaign.id, fb_asset.id, user_id=user.id)
    assert run.status == PASSED

    results = audit_service.list_results(db, run.id)
    result_titles = [r.title for r in results]

    # Globális szabály érvényesült
    assert any("Podravka" in t for t in result_titles)
    # Social szabály érvényesült
    assert any("bioban" in t for t in result_titles)
    # A POS szabály NEM futott le a Facebook anyagon!
    assert not any("raklap" in t for t in result_titles)
    # A Deliverable-höz rendelt elvárt képi tartalom is lefutott és sikeres
    assert any("Várt tartalom" in t or "Kért képi tartalom" in t for t in result_titles)


def test_channel_workspace_ui_and_direct_slot_upload(admin, db, setup_campaign_channels):
    from io import BytesIO
    from app.modules.factsheet import service as fact_service

    client, campaign, user, ch_social, ch_pos, deliv_fb1, deliv_pos1 = setup_campaign_channels
    fact_service.set_fact(db, campaign.id, "promocio_idoszak", "2026. nov 1-30.", "brief", None, user.id)
    fact_service.set_fact(db, campaign.id, "fodij", "100.000 Ft utalvány", "brief", None, user.id)

    # 1. Kampány főoldal lekérése: csatorna kártyák és tényadat sáv megjelenése
    resp_camp = admin.get(f"/campaigns/{campaign.id}")
    assert resp_camp.status_code == 200
    html_camp = resp_camp.text
    assert "Facebook / Social" in html_camp
    assert "Munkatér megnyitása" in html_camp
    assert "2026. nov 1-30." in html_camp
    assert "100.000 Ft utalvány" in html_camp

    # 2. Egyedi csatorna munkatér lekérése (Facebook csatorna)
    resp_ch = admin.get(f"/campaigns/{campaign.id}/channels/{ch_social.id}")
    assert resp_ch.status_code == 200
    html_ch = resp_ch.text
    assert "FB Poszt #1 (Bejelentő)" in html_ch
    assert "Feltöltés &amp; Auditálás" in html_ch or "Feltöltés & Auditálás" in html_ch
    assert "Vásárolj 2 db terméket és nyerj!" in html_ch

    # 3. Közvetlen slot feltöltés erre a deliverable-re
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=500, height=300)
    page.insert_text((50, 50), "Podravka promóció FB poszt")
    file_content = doc.write()
    doc.close()

    upload_resp = admin.post(
        f"/campaigns/{campaign.id}/deliverables/{deliv_fb1.id}/upload",
        files={"file": ("FB_01_Ad.pdf", file_content, "application/pdf")},
        follow_redirects=True,
    )
    assert upload_resp.status_code == 200

    db.refresh(deliv_fb1)
    assert deliv_fb1.asset_id is not None

    asset = db.get(Asset, deliv_fb1.asset_id)
    assert asset is not None
    assert asset.channel_id == ch_social.id
    assert asset.deliverable_id == deliv_fb1.id

    # Automatikusan lefutott az audit
    last_run = audit_service.latest_run_for_asset(db, asset.id)
    assert last_run is not None

    # 4. Leválasztás (unlink) tesztelése
    unlink_resp = admin.post(
        f"/campaigns/{campaign.id}/deliverables/{deliv_fb1.id}/unlink",
        follow_redirects=True,
    )
    assert unlink_resp.status_code == 200
    db.refresh(deliv_fb1)
    assert deliv_fb1.asset_id is None


def test_channel_deliverable_crud_and_rulebook_explorer(admin, db, setup_campaign_channels):
    client, campaign, user, ch_social, ch_pos, deliv_fb1, deliv_pos1 = setup_campaign_channels

    # 1. Új várt anyag létrehozása csatornában
    create_resp = admin.post(
        f"/campaigns/{campaign.id}/channels/{ch_social.id}/deliverables",
        data={
            "name": "FB Sztori #1 (Új)",
            "specs": "1080x1920",
            "expected_copy": "Kattints a linkre!",
            "post_copy": "Sztori leírás",
            "file_pattern": "FB_Story*",
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200

    new_deliv = db.scalar(
        channel_service.select(channel_service.Deliverable).where(
            channel_service.Deliverable.channel_id == ch_social.id,
            channel_service.Deliverable.name == "FB Sztori #1 (Új)",
        )
    )
    assert new_deliv is not None
    assert new_deliv.specs == "1080x1920"
    new_deliv_id = new_deliv.id

    # 2. Várt anyag törlése
    del_resp = admin.post(
        f"/campaigns/{campaign.id}/channels/{ch_social.id}/deliverables/{new_deliv_id}/delete",
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    db.expire_all()
    assert db.get(channel_service.Deliverable, new_deliv_id) is None

    # 3. Szabálykönyv explorer ellenőrzése a kampányoldalon
    camp_resp = admin.get(f"/campaigns/{campaign.id}#rules")
    assert camp_resp.status_code == 200
    assert "Szabálykönyv &amp; Compliance Explorer" in camp_resp.text or "Szabálykönyv & Compliance Explorer" in camp_resp.text
    assert "Ügyfélszintű Brandbook" in camp_resp.text
    assert "Csatorna-specifikus" in camp_resp.text


