# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────
from starlette.testclient import TestClient


class TestDelete:
    def test_delete_returns_204(self, client: TestClient) -> None:
        r = client.delete("/items/1")
        assert r.status_code == 204

    def test_delete_removes_item(self, client: TestClient) -> None:
        client.delete("/items/1")
        r = client.get("/items/1")
        assert r.status_code == 404

    def test_delete_missing_returns_404(self, client: TestClient) -> None:
        r = client.delete("/items/999")
        assert r.status_code == 404

    def test_delete_reduces_list_length(self, client: TestClient) -> None:
        client.delete("/items/1")
        items = client.get("/items/").json()
        assert len(items) == 1
