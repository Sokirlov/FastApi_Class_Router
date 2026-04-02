"""
example.py — Full usage example for fastapi-class-router.
Run with: uvicorn example:app --reload
"""

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from fastapi_class_router import ClassRouter, delete, get, patch, post, put

# ── Schemas ───────────────────────────────────────────────────────────────────


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class UserCreate(BaseModel):
    name: str
    email: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


# ── Fake DB + dependencies ────────────────────────────────────────────────────

_DB: dict[int, dict[str, int | str]] = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}


def get_db() -> dict[int, dict[str, int | str]]:
    return _DB


def get_current_user() -> dict[str, Any]:
    # In a real app: verify JWT / session
    return {"id": 99, "role": "admin"}


# ── Controller ────────────────────────────────────────────────────────────────


class UserController(ClassRouter, prefix="/users", tags=["Users"]):
    """
    CRUD controller for User resources.

    All __init__ dependencies are resolved per-request by FastAPI —
    no manual Depends() wiring needed anywhere else.
    """

    def __init__(
        self,
        db: dict[int, dict[str, int | str]] = Depends(get_db),
        current_user: dict[str, Any] = Depends(get_current_user),
    ):
        self.db = db
        self.current_user = current_user

    @get("/", response_model=list[UserOut], summary="List users")
    async def list_users(self) -> list[dict[str, Any]]:
        return list(self.db.values())

    @get("/{user_id}", response_model=UserOut)
    async def get_user(self, user_id: int) -> dict[str, Any]:
        user = self.db.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    async def create_user(self, body: UserCreate) -> dict[str, Any]:
        new_id = max(self.db.keys(), default=0) + 1
        user = {"id": new_id, **body.model_dump()}
        self.db[new_id] = user
        return user

    @put("/{user_id}", response_model=UserOut)
    async def update_user(self, user_id: int, body: UserUpdate) -> dict[str, Any]:
        user = self.db.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        updated = {
            **user,
            **{k: v for k, v in body.model_dump().items() if v is not None},
        }
        self.db[user_id] = updated
        return updated

    @patch("/{user_id}", response_model=UserOut)
    async def patch_user(self, user_id: int, body: UserUpdate) -> dict[str, Any]:
        user = self.db.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if body.name is not None:
            user["name"] = body.name
        if body.email is not None:
            user["email"] = body.email
        return user

    @delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_user(self, user_id: int) -> None:
        if user_id not in self.db:
            raise HTTPException(status_code=404, detail="User not found")
        del self.db[user_id]


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="fastapi-class-router demo")

# Option A — simple
app.include_router(UserController.as_router())

# Option B — versioned parent router
# from fastapi import APIRouter
# v1 = APIRouter(prefix="/api/v1")
# UserController.attach_to(v1)
# app.include_router(v1)
