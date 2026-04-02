# ─────────────────────────────────────────────────────────────────────────────
# PATCH
# ─────────────────────────────────────────────────────────────────────────────
from starlette.testclient import TestClient


class TestPatch:
    def test_partial_update_returns_200(self, client: TestClient) -> None:
        r = client.patch("/items/1", json={"name": "Alpha-Patched"})
        assert r.status_code == 200

    def test_partial_update_changes_name(self, client: TestClient) -> None:
        client.patch("/items/1", json={"name": "Alpha-Patched"})
        assert client.get("/items/1").json()["name"] == "Alpha-Patched"

    def test_patch_missing_item_returns_404(self, client: TestClient) -> None:
        r = client.patch("/items/999", json={"name": "X"})
        assert r.status_code == 404

    def test_patch_null_field_no_change(self, client: TestClient) -> None:
        client.patch("/items/1", json={"name": None})
        assert client.get("/items/1").json()["name"] == "Alpha"
