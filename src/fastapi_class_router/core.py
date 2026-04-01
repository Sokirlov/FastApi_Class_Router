"""
ClassRouter — CBV-style controller wrapper for FastAPI.

Supports:
  - @get / @post / @put / @delete / @patch decorators on methods
  - Shared Depends in __init__ (injected per-request)
  - prefix, tags, dependencies, responses — full APIRouter compatibility
  - Auto-registration of decorated methods as endpoints
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Coroutine, Sequence
from enum import Enum
from typing import Any, ParamSpec, TypeVar, cast

from fastapi import APIRouter, params

# ── HTTP method marker ────────────────────────────────────────────────────────

_ROUTE_ATTR = "_route_meta"

T = TypeVar("T", bound=Callable[..., Any])
P = ParamSpec("P")
R = TypeVar("R")

# RouteHandler = Callable[P, R]


def _http(method: str) -> Callable[..., Callable[[Callable[P, R]], Callable[P, R]]]:
    """Factory that creates @get / @post / … decorators for controller methods."""

    def decorator(
        path: str,
        *,
        # Mirror the most common APIRouter.add_api_route kwargs
        response_model: Any = None,
        status_code: int | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        response_description: str = "Successful Response",
        deprecated: bool | None = None,
        operation_id: str | None = None,
        include_in_schema: bool = True,
        dependencies: Sequence[params.Depends] | None = None,
        responses: dict[int | str, dict[str, Any]] | None = None,
        **extra_kwargs: Any,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        def wrapper(fn: Callable[P, R]) -> Callable[P, R]:
            # Attach route metadata to the function — picked up at registration time
            router_data = {
                "method": method.upper(),
                "path": path,
                "response_model": response_model,
                "status_code": status_code,
                "tags": tags,
                "summary": summary,
                "description": description,
                "response_description": response_description,
                "deprecated": deprecated,
                "operation_id": operation_id,
                "include_in_schema": include_in_schema,
                "dependencies": dependencies or [],
                "responses": responses or {},
                **extra_kwargs,
            }

            setattr(fn, _ROUTE_ATTR, router_data)
            return fn

        return wrapper

    return decorator


# Public decorators — use these inside your controller
get = _http("GET")
post = _http("POST")
put = _http("PUT")
delete = _http("DELETE")
patch = _http("PATCH")


# ── ClassRouter metaclass ─────────────────────────────────────────────────────


class ClassRouterMeta(type):
    """
    Metaclass that collects all route-decorated methods and stores them
    in `__routes__` so the router can register them later.
    """

    def __new__(
        mcs: type[ClassRouterMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> ClassRouterMeta:
        routes_map: dict[str, Callable[..., Any]] = {}

        # Inherit routes from base classes first
        for base in bases:
            parent_routes = getattr(base, "__routes_map__", {})
            routes_map.update(parent_routes)

        # Collect methods decorated with route metadata
        for attr_name, value in namespace.items():
            if callable(value) and hasattr(value, _ROUTE_ATTR):
                routes_map[attr_name] = value

        # 3. Save the dictionary for subclasses and
        # the list for compatibility with other code
        namespace["__routes_map__"] = routes_map
        namespace["__routes__"] = list(routes_map.items())

        return super().__new__(mcs, name, bases, namespace, **kwargs)


# ── Base controller ───────────────────────────────────────────────────────────


class ClassRouter(metaclass=ClassRouterMeta):
    """
    Base class for controller-style routers.

    Usage
    -----
    class UserController(ClassRouter, prefix="/users", tags=["users"]):
        def __init__(self, db: Session = Depends(get_db)):
            self.db = db          # injected per request

        @get("/")
        async def list_users(self) -> list[UserSchema]:
            return self.db.query(User).all()

        @post("/", status_code=201)
        async def create_user(self, body: UserCreate) -> UserSchema:
            ...

    # Register with FastAPI app:
    app.include_router(UserController.as_router())

    # Or attach to an existing APIRouter:
    parent_router = APIRouter(prefix="/api/v1")
    UserController.attach_to(parent_router)
    app.include_router(parent_router)
    """

    # Class-level router configuration — can be overridden via class kwargs
    __prefix__: str = ""
    __tags__: list[str | Enum] = []
    __dependencies__: Sequence[params.Depends] = []
    __responses__: dict[int | str, dict[str, Any]] = {}
    __routes__: list[tuple[str, Callable[..., Any]]] = []
    __signature__: inspect.Signature | None = None

    def __init_subclass__(
        cls,
        prefix: str = "",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
        responses: dict[int | str, dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        super().__init_subclass__(**kwargs)
        if prefix:
            cls.__prefix__ = prefix
        if tags is not None:
            cls.__tags__ = tags
        if dependencies is not None:
            cls.__dependencies__ = dependencies
        if responses is not None:
            cls.__responses__ = responses

    # ── APIRouter builder ─────────────────────────────────────────────────────

    @classmethod
    def as_router(cls) -> APIRouter:
        """Build and return a fully configured APIRouter for this controller."""
        router = APIRouter(
            prefix=cls.__prefix__,
            tags=cls.__tags__ if cls.__tags__ else None,
            dependencies=cls.__dependencies__,
            responses=cls.__responses__,
        )
        cls._register_routes(router)
        return router

    @classmethod
    def attach_to(cls, router: APIRouter) -> None:
        """Register this controller's routes directly onto an existing APIRouter."""
        sub = cls.as_router()
        router.include_router(sub)

    # ── Internal registration ─────────────────────────────────────────────────

    @classmethod
    def _register_routes(cls, router: APIRouter) -> None:
        for attr_name, method_fn in cls.__routes__:
            cls._bind_route(router, attr_name, method_fn)

    @classmethod
    def _bind_route(
        cls,
        router: APIRouter,
        attr_name: str,
        method_fn: Callable[..., Any],
    ) -> None:
        meta: dict[Any, Any] = getattr(method_fn, _ROUTE_ATTR).copy()
        http_method = meta.pop("method")
        path = meta.pop("path")

        # Build a per-request factory endpoint:
        # FastAPI will inject __init__ dependencies (e.g. db: Session = Depends(get_db))
        # automatically because we declare `self: cls` using Depends.
        endpoint = cls._make_endpoint(cls, method_fn)

        router.add_api_route(
            path,
            endpoint,
            methods=[http_method],
            **meta,
        )

    @staticmethod
    def _make_endpoint(
        controller_cls: type[ClassRouter],
        fn: Callable[..., T],
    ) -> Callable[..., Coroutine[Any, Any, T]] | Callable[..., T]:
        """
        Wrap a controller method so that FastAPI instantiates the controller
        (resolving __init__ dependencies) and then calls the method.
        """
        # Inspect the original method signature (skip `self`)
        original_sig = inspect.signature(fn)
        method_params = [
            p for name, p in original_sig.parameters.items() if name != "self"
        ]

        # Inspect __init__ to get controller-level dependencies
        init_sig = inspect.signature(controller_cls.__init__)
        init_params = [p for name, p in init_sig.parameters.items() if name != "self"]

        # Build merged parameter list: controller deps first, then method params
        # FastAPI resolves each independently via the signature
        all_params = init_params + method_params

        # Generate the async/sync wrapper dynamically so FastAPI sees the correct
        # signature and resolves dependencies properly
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_endpoint(**kwargs: Any) -> T:
                init_kwargs = {
                    p.name: kwargs[p.name] for p in init_params if p.name in kwargs
                }
                method_kwargs = {
                    p.name: kwargs[p.name] for p in method_params if p.name in kwargs
                }
                instance = controller_cls(**init_kwargs)
                return cast(T, await fn(instance, **method_kwargs))

            _patch_signature(async_endpoint, all_params)
            return async_endpoint
        else:

            @functools.wraps(fn)
            def sync_endpoint(**kwargs: Any) -> T:
                init_kwargs = {
                    p.name: kwargs[p.name] for p in init_params if p.name in kwargs
                }
                method_kwargs = {
                    p.name: kwargs[p.name] for p in method_params if p.name in kwargs
                }
                instance = controller_cls(**init_kwargs)
                return fn(instance, **method_kwargs)

            _patch_signature(sync_endpoint, all_params)
            return sync_endpoint


def _patch_signature(
    fn: Callable[..., Coroutine[Any, Any, T]] | Callable[..., T],
    params: list[inspect.Parameter],
) -> None:
    """Replace function signature so FastAPI can introspect dependencies correctly."""
    sorted_params = sorted(params, key=lambda p: p.kind)
    cast(Any, fn).__signature__ = inspect.Signature(sorted_params)
