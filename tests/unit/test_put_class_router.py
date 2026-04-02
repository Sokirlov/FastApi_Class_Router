# ─────────────────────────────────────────────────────────────────────────────
# PUT
# ─────────────────────────────────────────────────────────────────────────────
from starlette.testclient import TestClient


class TestPut:
    def test_full_update_returns_200(self, client: TestClient) -> None:
        r = client.put("/items/1", json={"name": "Alpha-Updated"})
        assert r.status_code == 200

    def test_full_update_changes_name(self, client: TestClient) -> None:
        client.put("/items/1", json={"name": "Alpha-Updated"})
        r = client.get("/items/1")
        assert r.json()["name"] == "Alpha-Updated"

    def test_put_missing_item_returns_404(self, client: TestClient) -> None:
        r = client.put("/items/999", json={"name": "X"})
        assert r.status_code == 404
