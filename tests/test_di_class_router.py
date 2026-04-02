from typing import Any

from fastapi import Depends

from fastapi_class_router import ClassRouter, get
from tests.conftest import make_client

# ─────────────────────────────────────────────────────────────────────────────
# Dependency Injection
# ─────────────────────────────────────────────────────────────────────────────


class TestDependencyInjection:
    def test_init_dep_injected_per_request(self) -> None:
        """Each request gets its own controller instance via __init__ Depends."""
        call_count = {"n": 0}

        def counting_dep() -> int:
            call_count["n"] += 1
            return call_count["n"]

        class CountingCtrl(ClassRouter, prefix="/count"):
            def __init__(self, n: int = Depends(counting_dep)):
                self.n = n

            @get("/")
            async def show(self) -> dict[str, int]:
                return {"n": self.n}

        c = make_client(CountingCtrl)
        r1 = c.get("/count/")
        r2 = c.get("/count/")
        assert r1.json()["n"] == 1
        assert r2.json()["n"] == 2

    def test_route_level_dep(self) -> None:
        """Depends declared on a method parameter is also resolved correctly."""

        def extra() -> str:
            return "injected"

        class DepCtrl(ClassRouter, prefix="/dep"):
            def __init__(self) -> None:
                pass

            @get("/")
            async def show(self, val: str = Depends(extra)) -> dict[str, str]:
                return {"val": val}

        c = make_client(DepCtrl)
        assert c.get("/dep/").json() == {"val": "injected"}

    def test_class_level_dep_shared_across_routes(self) -> None:
        """__init__ dependency is resolved independently for each route call."""
        shared = {"value": "shared"}

        def shared_dep() -> dict[str, str]:
            return shared

        class SharedCtrl(ClassRouter, prefix="/shared"):
            def __init__(self, data: dict[Any, Any] = Depends(shared_dep)):
                self.data = data

            @get("/a")
            async def route_a(self) -> dict[Any, Any]:
                return self.data

            @get("/b")
            async def route_b(self) -> dict[Any, Any]:
                return self.data

        c = make_client(SharedCtrl)
        assert c.get("/shared/a").json() == {"value": "shared"}
        assert c.get("/shared/b").json() == {"value": "shared"}
