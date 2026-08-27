from fastapi import APIRouter

from ..limiter import auth_limiter, limiter
from . import auth, bag, profile, provider, telegram

__all__ = ["router"]

router = APIRouter(prefix="/v1")
router.include_router(telegram.router)
router.include_router(auth.router, dependencies=[auth_limiter])
router.include_router(bag.router, dependencies=[limiter])
router.include_router(profile.router)
router.include_router(provider.router, dependencies=[limiter])
