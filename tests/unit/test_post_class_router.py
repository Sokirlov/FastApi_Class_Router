# ─────────────────────────────────────────────────────────────────────────────
# POST
# ─────────────────────────────────────────────────────────────────────────────
from starlette.testclient import TestClient


class TestPost:
    def test_create_item_returns_201(self, client: TestClient) -> None:
        r = client.post("/items/", json={"name": "Gamma"})
        assert r.status_code == 201

    def test_create_item_returns_body(self, client: TestClient) -> None:
        r = client.post("/items/", json={"name": "Gamma"})
        body = r.json()
        assert body["name"] == "Gamma"
        assert "id" in body

    def test_create_item_persists(self, client: TestClient) -> None:
        r = client.post("/items/", json={"name": "Delta"})
        new_id = r.json()["id"]
        r2 = client.get(f"/items/{new_id}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "Delta"

    def test_create_assigns_unique_ids(self, client: TestClient) -> None:
        id1 = client.post("/items/", json={"name": "X"}).json()["id"]
        id2 = client.post("/items/", json={"name": "Y"}).json()["id"]
        assert id1 != id2

    def test_create_missing_body_returns_422(self, client: TestClient) -> None:
        r = client.post("/items/", json={})
        assert r.status_code == 422
