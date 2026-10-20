import fitz
import pytest

from app.modules.assets import service
from app.modules.tenants import service as tenants


@pytest.fixture()
def sample_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page(width=500, height=300)
    page.insert_text((50, 50), "Podravka Nyereményjáték")
    page.insert_text((50, 100), "Időtartam: 2026. november 5 - 18.")
    page.insert_text((50, 150), "Részletek: www.podravkanyeremenyjatek.hu")
    data = doc.write()
    doc.close()
    return data


def test_save_and_ingest_pdf(db, tmp_path, sample_pdf_bytes):
    client = tenants.create_client(db, "Kliens")
    campaign = tenants.create_campaign(db, client.id, "Kampany")

    asset = service.save_and_ingest(
        db, campaign.id, "teszt.pdf", sample_pdf_bytes,
        up_dir=str(tmp_path / "uploads"), prev_dir=str(tmp_path / "previews")
    )

    assert asset.name == "teszt.pdf"
    assert asset.file_type == "pdf"
    assert asset.page_count == 1
    assert asset.preview_path != ""

    content = service.get_content(db, asset.id)
    assert content is not None
    assert "Podravka Nyereményjáték" in content.plain_text
    assert "www.podravkanyeremenyjatek.hu" in content.plain_text
    assert len(content.blocks) > 0


def test_scan_local_folder(db, tmp_path, sample_pdf_bytes):
    client = tenants.create_client(db, "Kliens2")
    campaign = tenants.create_campaign(db, client.id, "Kampany2")

    folder = tmp_path / "projekt_mappa"
    folder.mkdir()
    (folder / "promo1.pdf").write_bytes(sample_pdf_bytes)
    (folder / "nem_tamogatott.txt").write_text("szia", encoding="utf-8")

    assets = service.scan_local_folder(db, campaign.id, str(folder), prev_dir=str(tmp_path / "previews"))
    assert len(assets) == 1
    assert assets[0].name == "promo1.pdf"
