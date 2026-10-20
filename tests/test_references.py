import io
from PIL import Image
import pytest

from app.modules.audits.ai.embedder import FeatureHashEmbedder, cosine_similarity
from app.modules.references import service as ref_service
from app.modules.tenants import service as tenants


@pytest.fixture()
def sample_image_bytes():
    img = Image.new("RGB", (200, 200), color=(30, 80, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_embedder_similarity(tmp_path, sample_image_bytes):
    embedder = FeatureHashEmbedder()
    p1 = tmp_path / "img1.png"
    p2 = tmp_path / "img2.png"
    p1.write_bytes(sample_image_bytes)
    p2.write_bytes(sample_image_bytes)

    v1 = embedder.embed_image(str(p1))
    v2 = embedder.embed_image(str(p2))

    assert len(v1) == 64
    sim = cosine_similarity(v1, v2)
    assert sim >= 0.99  # Azonos kép esetén 1.0


def test_add_and_list_references(db, tmp_path, sample_image_bytes):
    client = tenants.create_client(db, "Márka")
    campaign = tenants.create_campaign(db, client.id, "Kampány")

    ref = ref_service.add_reference(
        db, "campaign", campaign.id, "Hivatalos Logó", "logo",
        sample_image_bytes, "logo.png", storage_dir=str(tmp_path / "refs")
    )
    assert ref.id is not None
    assert ref.name == "Hivatalos Logó"
    assert len(ref.embedding) == 64

    refs = ref_service.list_references(db, "campaign", campaign.id)
    assert len(refs) == 1

    ref_service.delete_reference(db, ref.id)
    assert len(ref_service.list_references(db, "campaign", campaign.id)) == 0
