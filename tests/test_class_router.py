"""
Tests for fastapi-class-router.

Coverage:
  - All HTTP methods: GET, POST, PUT, DELETE, PATCH
  - Path and query parameters
  - Request body (Pydantic models)
  - __init__ Depends injection (per-request)
  - Route-level Depends
  - prefix / tags / responses class kwargs
  - as_router() and attach_to()
  - Route inheritance from base controllers
  - Sync and async endpoints
  - include_in_schema / deprecated / operation_id passthrough
  - 204 No Content (empty response body)
"""

from typing import Any, cast

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_class_router import ClassRouter, get, post
from tests.conftest import ItemCreate, make_client

# ─────────────────────────────────────────────────────────────────────────────
# Router configuration (prefix, tags, responses)
# ─────────────────────────────────────────────────────────────────────────────


class TestRouterConfig:
    def test_prefix_applied(self) -> None:
        class PrefixCtrl(ClassRouter, prefix="/api/v1/things"):
            def __init__(self) -> None:
                pass

            @get("/")
            async def index(self) -> list[None]:
                return []

        c = make_client(PrefixCtrl)
        assert c.get("/api/v1/things/").status_code == 200

    def test_no_prefix_still_works(self) -> None:
        class NoPrefixCtrl(ClassRouter):
            def __init__(self) -> None:
                pass

            @get("/root")
            async def index(self) -> dict[str, bool]:
                return {"ok": True}

        c = make_client(NoPrefixCtrl)
        assert c.get("/root").status_code == 200

    def test_tags_appear_in_openapi(self) -> None:
        class TaggedCtrl(ClassRouter, prefix="/tagged", tags=["my-tag"]):
            def __init__(self) -> None:
                pass

            @get("/")
            async def index(self) -> dict[str, None]:
                return {}

        app = FastAPI()
        app.include_router(TaggedCtrl.as_router())
        c = TestClient(app)
        schema = c.get("/openapi.json").json()
        tags = [
            tag
            for path_item in schema["paths"].values()
            for op in path_item.values()
            for tag in op.get("tags", [])
        ]
        assert "my-tag" in tags

    def test_class_level_dependencies_applied(self) -> None:
        """Class-level Depends is called for every route in the controller."""
        called = {"times": 0}

        def guard() -> None:
            called["times"] += 1

        class GuardedCtrl(
            ClassRouter, prefix="/guarded", dependencies=[Depends(guard)]
        ):
            def __init__(self) -> None:
                pass

            @get("/a")
            async def a(self) -> dict[str, None]:
                return {}

            @get("/b")
            async def b(self) -> dict[str, None]:
                return {}

        c = make_client(GuardedCtrl)
        c.get("/guarded/a")
        c.get("/guarded/b")
        assert called["times"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# as_router() vs attach_to()
# ─────────────────────────────────────────────────────────────────────────────


class TestAttachTo:
    def test_attach_to_parent_router(self) -> None:
        from fastapi import APIRouter

        class AttachCtrl(ClassRouter, prefix="/attach"):
            def __init__(self) -> None:
                pass

            @get("/ping")
            async def ping(self) -> dict[str, bool]:
                return {"pong": True}

        parent = APIRouter(prefix="/api/v1")
        AttachCtrl.attach_to(parent)

        app = FastAPI()
        app.include_router(parent)
        c = TestClient(app)
        assert c.get("/api/v1/attach/ping").status_code == 200

    def test_as_router_returns_api_router(self) -> None:
        from fastapi import APIRouter as AR

        class SimpleCtrl(ClassRouter, prefix="/x"):
            def __init__(self) -> None:
                pass

            @get("/")
            async def index(self) -> dict[str, None]:
                return {}

        router = SimpleCtrl.as_router()
        assert isinstance(router, AR)


# ─────────────────────────────────────────────────────────────────────────────
# Route inheritance
# ─────────────────────────────────────────────────────────────────────────────


class TestInheritance:
    def test_child_inherits_parent_routes(self) -> None:
        class BaseCtrl(ClassRouter, prefix="/base"):
            def __init__(self) -> None:
                pass

            @get("/hello")
            async def hello(self) -> dict[str, str]:
                return {"from": "base"}

        class ChildCtrl(BaseCtrl, prefix="/child"):
            pass

        c = make_client(ChildCtrl)
        r = c.get("/child/hello")
        assert r.status_code == 200
        assert r.json() == {"from": "base"}

    def test_child_can_override_parent_route(self) -> None:
        class BaseCtrl2(ClassRouter, prefix="/base2"):
            def __init__(self) -> None:
                pass

            @get("/info")
            async def info(self) -> dict[str, str]:
                return {"source": "base"}

        class ChildCtrl2(BaseCtrl2, prefix="/child2"):
            @get("/info")
            async def info(self) -> dict[str, str]:
                return {"source": "child"}

        c = make_client(ChildCtrl2)
        assert c.get("/child2/info").json() == {"source": "child"}

    def test_multiple_controllers_independent(self) -> None:
        class CtrlA(ClassRouter, prefix="/a"):
            def __init__(self) -> None:
                pass

            @get("/")
            async def index(self) -> dict[str, str]:
                return {"ctrl": "A"}

        class CtrlB(ClassRouter, prefix="/b"):
            def __init__(self) -> None:
                pass

            @get("/")
            async def index(self) -> dict[str, str]:
                return {"ctrl": "B"}

        c = make_client(CtrlA, CtrlB)
        assert c.get("/a/").json() == {"ctrl": "A"}
        assert c.get("/b/").json() == {"ctrl": "B"}


# ─────────────────────────────────────────────────────────────────────────────
# Sync endpoints
# ─────────────────────────────────────────────────────────────────────────────


class TestSyncEndpoints:
    def test_sync_get(self) -> None:
        class SyncCtrl(ClassRouter, prefix="/sync"):
            def __init__(self) -> None:
                pass

            @get("/")
            def index(self) -> dict[str, bool]:
                return {"sync": True}

        c = make_client(SyncCtrl)
        assert c.get("/sync/").json() == {"sync": True}

    def test_sync_post(self) -> None:
        class SyncPostCtrl(ClassRouter, prefix="/syncpost"):
            def __init__(self) -> None:
                pass

            @post("/")
            def create(self, body: ItemCreate) -> dict[str, str]:
                return {"name": body.name}

        c = make_client(SyncPostCtrl)
        assert c.post("/syncpost/", json={"name": "Sync"}).json() == {"name": "Sync"}


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI / schema passthrough
# ─────────────────────────────────────────────────────────────────────────────


class TestOpenAPIPassthrough:
    def _schema(self, ctrl: type[ClassRouter]) -> dict[str, Any]:
        app = FastAPI()
        app.include_router(ctrl.as_router())
        response = TestClient(app).get("/openapi.json")
        return cast(dict[str, Any], response.json())

    def test_deprecated_flag(self) -> None:
        class DeprecatedCtrl(ClassRouter, prefix="/old"):
            def __init__(self) -> None:
                pass

            @get("/", deprecated=True)
            async def index(self) -> dict[str, None]:
                return {}

        schema = self._schema(DeprecatedCtrl)
        op = schema["paths"]["/old/"]["get"]
        assert op.get("deprecated") is True

    def test_operation_id(self) -> None:
        class OpIdCtrl(ClassRouter, prefix="/opid"):
            def __init__(self) -> None:
                pass

            @get("/", operation_id="custom_op_id")
            async def index(self) -> dict[str, None]:
                return {}

        schema = self._schema(OpIdCtrl)
        op = schema["paths"]["/opid/"]["get"]
        assert op["operationId"] == "custom_op_id"

    def test_include_in_schema_false(self) -> None:
        class HiddenCtrl(ClassRouter, prefix="/hidden"):
            def __init__(self) -> None:
                pass

            @get("/", include_in_schema=False)
            async def index(self) -> dict[str, None]:
                return {}

        schema = self._schema(HiddenCtrl)
        assert "/hidden/" not in schema["paths"]

    def test_summary_and_description(self) -> None:
        class DocCtrl(ClassRouter, prefix="/doc"):
            def __init__(self) -> None:
                pass

            @get("/", summary="My summary", description="My description")
            async def index(self) -> dict[str, str | None]:
                return {}

        schema = self._schema(DocCtrl)
        op = schema["paths"]["/doc/"]["get"]
        assert op["summary"] == "My summary"
        assert op["description"] == "My description"
