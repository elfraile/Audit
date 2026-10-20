from app.modules.accounts import access, service
from app.modules.tenants import service as tenants


def test_login_and_roles(client, admin):
    assert admin.get("/api/me").json()["role"] == "admin"
    assert admin.post("/api/users", json={"email": "a@t.local", "name": "A", "password": "x",
                                          "role": "bogus"}).status_code == 400


def test_unauthenticated_blocked(client):
    assert client.get("/api/clients").status_code == 401


def test_access_scoping(db):
    c1, c2 = tenants.create_client(db, "C1"), tenants.create_client(db, "C2")
    camp_a = tenants.create_campaign(db, c1.id, "A")
    camp_b = tenants.create_campaign(db, c1.id, "B")
    user = service.create_user(db, "u@t.local", "U", "x", "editor")
    access.grant_access(db, user.id, c1.id, camp_a.id)
    assert access.can_access(db, user, c1.id) is True
    assert access.can_access(db, user, c1.id, camp_a.id) is True
    assert access.can_access(db, user, c1.id, camp_b.id) is False
    assert access.can_access(db, user, c2.id) is False
    assert [c.id for c in tenants.campaigns_for(db, user, c1.id)] == [camp_a.id]


def test_hierarchy_via_api(admin):
    client_id = admin.post("/api/clients", json={"name": "X"}).json()["id"]
    assert admin.post("/api/clients", json={"name": "X"}).status_code == 400
    admin.post(f"/api/clients/{client_id}/campaigns", json={"name": "K"})
    assert len(admin.get(f"/api/clients/{client_id}/campaigns").json()) == 1
