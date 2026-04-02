# fastapi-class-router

CBV-style (class-based views) controller wrapper for [FastAPI](https://fastapi.tiangolo.com/) that preserves **100% of `APIRouter` functionality**.

---

## Features

- `@get`, `@post`, `@put`, `@delete`, `@patch` decorators directly on class methods
- `__init__` dependencies resolved per-request via FastAPI's `Depends` — shared across all routes in the controller
- Full `APIRouter` compatibility: `prefix`, `tags`, `dependencies`, `responses`
- Route inheritance — child controllers inherit routes from parent classes
- `as_router()` and `attach_to()` for flexible integration
- Sync and `async` endpoints both supported
- OpenAPI schema passthrough: `summary`, `description`, `deprecated`, `operation_id`, `include_in_schema`

---

## Installation

```bash
pip install fastapi-class-router
```

Requires Python ≥ 3.10 and FastAPI ≥ 0.100.

---

## Quick Start

```python
from fastapi import FastAPI, Depends
from fastapi_class_router import ClassRouter, get, post, put, delete

app = FastAPI()

# ── Dependencies ──────────────────────────────────────────────────────────────

def get_db():
    return {"connected": True}   # replace with a real session

# ── Schema ────────────────────────────────────────────────────────────────────

from pydantic import BaseModel

class ItemOut(BaseModel):
    id: int
    name: str

class ItemCreate(BaseModel):
    name: str

# ── Controller ────────────────────────────────────────────────────────────────

class ItemController(ClassRouter, prefix="/items", tags=["Items"]):
    """
    All dependencies declared in __init__ are injected per-request by FastAPI.
    No manual Depends() wiring needed on individual methods.
    """

    def __init__(self, db=Depends(get_db)):
        self.db = db

    @get("/", response_model=list[ItemOut])
    async def list_items(self):
        return []

    @post("/", response_model=ItemOut, status_code=201)
    async def create_item(self, body: ItemCreate):
        return {"id": 1, "name": body.name}

# ── Register ──────────────────────────────────────────────────────────────────

app.include_router(ItemController.as_router())
```

---

## Class kwargs

| kwarg          | Type         | Description                                          |
|----------------|--------------|------------------------------------------------------|
| `prefix`       | `str`        | URL prefix applied to all routes                     |
| `tags`         | `list[str]`  | OpenAPI tags for all routes                          |
| `dependencies` | `list`       | `Depends(...)` applied to every route in the class   |
| `responses`    | `dict`       | Shared response definitions                          |

```python
class SecureController(
    ClassRouter,
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
    responses={403: {"description": "Forbidden"}},
):
    ...
```

---

## Route decorators

All decorators accept the same kwargs as `APIRouter.add_api_route`:

```python
@get(
    "/",
    response_model=list[ItemOut],
    status_code=200,
    summary="List all items",
    description="Returns a paginated list of items.",
    deprecated=False,
    operation_id="list_items",
    include_in_schema=True,
    dependencies=[Depends(log_request)],
    responses={429: {"description": "Rate limited"}},
)
async def list_items(self):
    ...
```

---

## Dependency Injection

### Controller-level (shared across all routes)

```python
class ReportController(ClassRouter, prefix="/reports"):
    def __init__(
        self,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        self.db = db
        self.current_user = current_user

    @get("/")
    async def list_reports(self):
        # self.db and self.current_user are available here
        ...
```

### Route-level (specific to one endpoint)

```python
@get("/export")
async def export(self, fmt: str = Depends(parse_format)):
    ...
```

Both levels can be combined freely.

---

## Registration options

### Option 1 — directly on the app

```python
app.include_router(ItemController.as_router())
```

### Option 2 — attach to an existing router (versioning)

```python
from fastapi import APIRouter

v1 = APIRouter(prefix="/api/v1")
ItemController.attach_to(v1)
UserController.attach_to(v1)

app.include_router(v1)
```

---

## Inheritance

Child controllers automatically inherit routes from their parents. Overriding a route is as simple as redefining the method:

```python
class BaseController(ClassRouter, prefix="/base"):
    def __init__(self): pass

    @get("/hello")
    async def hello(self):
        return {"msg": "from base"}


class ChildController(BaseController, prefix="/child"):
    @get("/hello")          # overrides the parent route
    async def hello(self):
        return {"msg": "from child"}
```

---
