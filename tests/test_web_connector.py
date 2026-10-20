from pathlib import Path
import pytest
from app.modules.assets import web_connector
from app.modules.assets.models import Asset, AssetContent
from app.modules.tenants import service as tenants


def test_is_xd_url():
    assert web_connector.is_xd_url("https://xd.adobe.com/view/767108b9-a3af-4fd2-8cf6-d453868c8f26-2322/")
    assert web_connector.is_xd_url("https://XD.ADOBE.COM/view/xyz")
    assert not web_connector.is_xd_url("https://example.com/landing")
    assert not web_connector.is_xd_url("https://brand.client.com")


def test_browser_detection():
    browser = web_connector.find_browser_executable()
    # Windows környezetben a Chrome vagy az Edge telepítve van
    assert browser is not None
    assert Path(browser).exists()


def test_generate_card_preview(tmp_path):
    target = tmp_path / "card.png"
    p = web_connector._generate_web_card_preview("https://example.com", "Cím", "Tartalom leírás", target)
    assert Path(p).exists()
    assert Path(p).stat().st_size > 100


def test_ingest_url_generic(db, tmp_path, monkeypatch):
    client = tenants.create_client(db, "Web Ügyfél")
    campaign = tenants.create_campaign(db, client.id, "Web Kampány")

    # Mock fetch_web_content a hálózati függetlenséghez unit tesztben
    def mock_fetch(url, prev_dir):
        fake_prev = tmp_path / "fake_prev.png"
        fake_prev.write_bytes(b"dummy_image_data")
        return (
            "Akciós Ajánlat - Weboldal",
            "Üdvözöljük! Akció érvényes 2026. november 1-ig.",
            [{"page": 0, "bbox": [0, 0, 100, 100], "text": "Üdvözöljük!"}],
            str(fake_prev)
        )

    monkeypatch.setattr(web_connector, "fetch_web_content", mock_fetch)

    asset = web_connector.ingest_url(
        db, campaign.id, "https://promo.brand.com/landing",
        name="Landing Page", prev_dir=str(tmp_path)
    )

    assert asset.id is not None
    assert asset.campaign_id == campaign.id
    assert asset.file_type == "web"
    assert asset.name == "Landing Page"

    content = db.get(AssetContent, 1)
    assert content is not None
    assert "Akció érvényes" in content.plain_text
    assert len(content.blocks) == 1


def test_ingest_url_xd_type(db, tmp_path, monkeypatch):
    client = tenants.create_client(db, "XD Ügyfél")
    campaign = tenants.create_campaign(db, client.id, "XD Kampány")

    def mock_fetch(url, prev_dir):
        fake_prev = tmp_path / "fake_xd.png"
        fake_prev.write_bytes(b"dummy_xd_preview")
        return (
            "Podravka Auchan Microsite Terv",
            "Artboard: Főoldal\nArtboard: Aloldal",
            [{"page": 0, "bbox": [0, 0, 100, 100], "text": "Artboard: Főoldal"}],
            str(fake_prev)
        )

    monkeypatch.setattr(web_connector, "fetch_web_content", mock_fetch)

    xd_url = "https://xd.adobe.com/view/767108b9-a3af-4fd2-8cf6-d453868c8f26-2322/"
    asset = web_connector.ingest_url(db, campaign.id, xd_url, prev_dir=str(tmp_path))

    assert asset.id is not None
    assert asset.file_type == "xd"
    assert "Podravka Auchan" in asset.name
