from pathlib import Path
import pytest

from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.audits.models import PASSED
from app.modules.factsheet import service as fact_service
from app.modules.rules import lifecycle
from app.modules.tenants import service as tenants

REAL_PROMO_DIR = Path(r"W:\AI\Projects\Audit\Research\Podravka Projekt")


@pytest.mark.skipif(not REAL_PROMO_DIR.is_dir(), reason="Nincs elérhető valós tesztkönyvtár")
def test_real_podravka_promo_audit(db, tmp_path):
    client = tenants.create_client(db, "Podravka")
    campaign = tenants.create_campaign(db, client.id, "Auchan TM Promóció")

    # 1. Tényadatok rögzítése a brief és ütemterv alapján
    fact_service.set_fact(db, campaign.id, "url", "www.podravkanyeremenyjatek.hu")
    fact_service.set_fact(db, campaign.id, "idopont", "2026. november 5 - 18.")
    fact_service.set_fact(db, campaign.id, "fodij", "HOOVER Side by side hűtő")
    fact_service.set_fact(db, campaign.id, "heti", "2 x Tefal edénykészlet")

    # 2. Szabályok felvétele
    r1 = lifecycle.create_draft(db, "campaign", campaign.id, "Kötelező illusztráció disclaimer",
                                check={"must_contain": "A nyeremények képe illusztráció"})
    lifecycle.approve(db, r1.id)

    r2 = lifecycle.create_draft(db, "campaign", campaign.id, "Kötelező bizonylat megőrzés disclaimer",
                                check={"must_contain": "A bizonylatot kérjük, őrizd meg!"})
    lifecycle.approve(db, r2.id)

    r3 = lifecycle.create_draft(db, "campaign", campaign.id, "Tiltott kifejezés teszt",
                                check={"forbidden": "Luxuspihenés"})
    lifecycle.approve(db, r3.id)

    # 3. Valós PDF-ek beolvasása a megadott mappából
    pdf_files = list(REAL_PROMO_DIR.glob("*.pdf"))
    assert len(pdf_files) >= 2

    for pdf in pdf_files:
        asset = asset_service.ingest_existing_file(
            db, campaign.id, str(pdf), prev_dir=str(tmp_path / "previews")
        )
        assert asset.id is not None
        assert asset.file_type == "pdf"
        assert Path(asset.preview_path).exists()

        # Szöveges tartalom vizsgálata
        content = asset_service.get_content(db, asset.id)
        assert content is not None
        assert len(content.plain_text) > 100
        assert len(content.blocks) > 0

        # Audit lefutása a valós anyagon
        run = audit_service.run_audit(db, campaign.id, asset.id)
        assert run.status == PASSED
        assert run.failed_count == 0
        assert run.passed_count >= 7  # 4 fact + 3 rule

        # Bounding box ellenőrzése legalább egy eredményre
        results = audit_service.list_results(db, run.id)
        has_bbox = any("bbox" in (r.evidence or {}) for r in results)
        assert has_bbox is True
