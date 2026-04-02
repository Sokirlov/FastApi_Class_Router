from starlette.testclient import TestClient

from tests.unit.conftest import _STORE

# ─────────────────────────────────────────────────────────────────────────────
# GET
# ─────────────────────────────────────────────────────────────────────────────


class TestGet:
    def test_list_returns_all_items(self, client: TestClient) -> None:
        r = client.get("/items/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert any(i["name"] == "Alpha" for i in data)

    def test_get_existing_item(self, client: TestClient) -> None:
        r = client.get("/items/1")
        assert r.status_code == 200
        assert r.json() == {"id": 1, "name": "Alpha"}

    def test_get_missing_item_returns_404(self, client: TestClient) -> None:
        r = client.get("/items/999")
        assert r.status_code == 404

    def test_list_empty_store(self, client: TestClient) -> None:
        _STORE.clear()
        r = client.get("/items/")
        assert r.status_code == 200
        assert r.json() == []
