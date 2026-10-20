import fitz
import pytest

from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.audits.engine import check_fact, check_rule
from app.modules.audits.models import FAILED, PASSED
from app.modules.factsheet import service as fact_service
from app.modules.issues import queries as issue_queries
from app.modules.rules import lifecycle
from app.modules.tenants import service as tenants


def test_rule_and_fact_engine():
    blocks = [{"page": 0, "bbox": [10, 10, 50, 50], "text": "Fődíj: HOOVER hűtő\nwww.podravkanyeremenyjatek.hu"}]
    full_text = "Fődíj: HOOVER hűtő\nwww.podravkanyeremenyjatek.hu"

    # Must contain
    v1, _, ev1 = check_rule("Kötelező URL", {"must_contain": "podravkanyeremenyjatek.hu"}, full_text, blocks)
    assert v1 == PASSED and ev1.get("bbox") == [10, 10, 50, 50]

    # Forbidden
    v2, _, _ = check_rule("Tiltott szó", {"forbidden": "Luxuspihenés"}, full_text, blocks)
    assert v2 == PASSED

    v2_fail, _, _ = check_rule("Tiltott szó", {"forbidden": "HOOVER"}, full_text, blocks)
    assert v2_fail == FAILED

    # Quotes in rule text
    v3, _, _ = check_rule('A kreatívnak tartalmaznia kell a „HOOVER hűtő” megnevezést', {}, full_text, blocks)
    assert v3 == PASSED

    # Fact check
    vf_pass = check_fact("URL", "www.podravkanyeremenyjatek.hu", full_text, blocks)
    assert vf_pass is not None and vf_pass[0] == PASSED

    vf_fail = check_fact("Időtartam", "2026. december", full_text, blocks)
    assert vf_fail is not None and vf_fail[0] == FAILED


def test_end_to_end_audit(db, tmp_path):
    client = tenants.create_client(db, "Podravka")
    campaign = tenants.create_campaign(db, client.id, "Auchan Promó")

    # Tényadatok rögzítése
    fact_service.set_fact(db, campaign.id, "url", "www.podravkanyeremenyjatek.hu")
    fact_service.set_fact(db, campaign.id, "idopont", "2026. november 5 - 18.")

    # Szabályok rögzítése és jóváhagyása
    r1 = lifecycle.create_draft(db, "campaign", campaign.id, 'Tartalmaznia kell a „HOOVER” szót')
    lifecycle.approve(db, r1.id)

    r2 = lifecycle.create_draft(db, "campaign", campaign.id, "Nem tartalmazhatja", check={"forbidden": "TiltottSzó"})
    lifecycle.approve(db, r2.id)

    r3 = lifecycle.create_draft(db, "campaign", campaign.id, "Hiányzó elem", check={"must_contain": "NemLétezőKifejezés"})
    lifecycle.approve(db, r3.id)

    # Asset létrehozása
    doc = fitz.open()
    page = doc.new_page(width=500, height=300)
    page.insert_text((50, 50), "HOOVER hűtő promóció")
    page.insert_text((50, 100), "Időtartam: 2026. november 5 - 18.")
    page.insert_text((50, 150), "Részletek: www.podravkanyeremenyjatek.hu")
    pdf_bytes = doc.write()
    doc.close()

    asset = asset_service.save_and_ingest(
        db, campaign.id, "standee.pdf", pdf_bytes,
        up_dir=str(tmp_path / "up"), prev_dir=str(tmp_path / "prev")
    )

    # Audit futtatása
    run = audit_service.run_audit(db, campaign.id, asset.id)
    assert run.status == FAILED  # r3 miatt (NemLétezőKifejezés)
    assert run.passed_count >= 4  # r1, r2, fact url, fact idopont
    assert run.failed_count == 1

    results = audit_service.list_results(db, run.id)
    failed_res = [r for r in results if r.verdict == FAILED][0]

    # Hibalista tétel készítése az audit hibából
    issue = issue_queries.list_issues(db, campaign.id)
    assert len(issue) == 0

    from app.modules.issues import service as issue_service
    new_issue = issue_service.create_issue(
        db, campaign.id, description=f"Audit: {failed_res.title}",
        asset_ref=asset.name, category=failed_res.category
    )
    assert new_issue.id is not None
    assert len(issue_queries.open_issues(db, campaign.id)) == 1
