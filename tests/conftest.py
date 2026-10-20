import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.factory import create_app


@pytest.fixture()
def app(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", secret_key="t",
                        admin_email="admin@t.local", admin_password="pw")
    return create_app(settings)


@pytest.fixture()
def db(app):
    with app.state.session_factory() as session:
        yield session


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def admin(client):
    client.post("/api/login", json={"email": "admin@t.local", "password": "pw"})
    return client
