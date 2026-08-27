from fastapi import APIRouter

from . import health, v1

__all__ = ["router"]

router = APIRouter()
router.include_router(health.router)
router.include_router(v1.router, prefix="/api")
