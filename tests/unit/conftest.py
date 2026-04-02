"""
Shared pytest fixtures for fastapi-class-router tests.
"""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from starlette.testclient import TestClient

from fastapi_class_router import ClassRouter, delete, get, patch, post, put

# ─────────────────────────────────────────────────────────────────────────────
# Helpers / shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


class ItemSchema(BaseModel):
    id: int
    name: str


class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: str | None = None


_STORE: dict[int, Any] = {}


def reset_store() -> None:
    _STORE.clear()
    _STORE.update(
        {
            1: {"id": 1, "name": "Alpha"},
            2: {"id": 2, "name": "Beta"},
        }
    )


def get_store() -> dict[int, Any]:
    return _STORE


def make_client(*controllers: type[ClassRouter]) -> TestClient:
    """Build a TestClient with one or more controllers registered."""
    app = FastAPI()
    for ctrl in controllers:
        app.include_router(ctrl.as_router())
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Basic CRUD controller (used by most tests)
# ─────────────────────────────────────────────────────────────────────────────


class ItemController(ClassRouter, prefix="/items", tags=["items"]):
    def __init__(self, store: dict[Any, Any] = Depends(get_store)):
        self.store = store

    @get("/", response_model=list[ItemSchema])
    async def list_items(self) -> list[ItemSchema]:
        return list(self.store.values())

    @get("/{item_id}", response_model=ItemSchema)
    async def get_item(self, item_id: int) -> Any:
        item = self.store.get(item_id)
        if not item:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        return item

    @post("/", response_model=ItemSchema, status_code=201)
    async def create_item(self, body: ItemCreate) -> dict[str, int | str | Any]:
        new_id = max(self.store.keys(), default=0) + 1
        item = {"id": new_id, "name": body.name}
        self.store[new_id] = item
        return item

    @put("/{item_id}", response_model=ItemSchema)
    async def update_item(self, item_id: int, body: ItemUpdate) -> Any:
        item = self.store.get(item_id)
        if not item:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        if body.name is not None:
            item["name"] = body.name
        return item

    @patch("/{item_id}", response_model=ItemSchema)
    async def patch_item(self, item_id: int, body: ItemUpdate) -> Any:
        item = self.store.get(item_id)
        if not item:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        if body.name is not None:
            item["name"] = body.name
        return item

    @delete("/{item_id}", status_code=204)
    async def delete_item(self, item_id: int) -> None:
        if item_id not in self.store:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        del self.store[item_id]


@pytest.fixture(autouse=True)
def fresh_store() -> Generator[None, None, None]:
    reset_store()
    yield


@pytest.fixture
def client() -> TestClient:
    return make_client(ItemController)
