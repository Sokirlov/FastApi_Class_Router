"""
fastapi-class-router
~~~~~~~~~~~~~~~~~~~~
CBV-style controller wrapper for FastAPI.
"""

from fastapi_class_router.core import (
    ClassRouter,
    delete,
    get,
    patch,
    post,
    put,
)

__all__ = [
    "ClassRouter",
    "get",
    "post",
    "put",
    "delete",
    "patch",
]

__version__ = "0.1.3"
