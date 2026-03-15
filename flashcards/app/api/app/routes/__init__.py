"""API router: all domain routers under /api (auth, sessions, cards, imports, metrics, tts, admin)."""

from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .cards import router as cards_router
from .imports import router as imports_router
from .metrics import router as metrics_router
from .sessions import router as sessions_router
from .tts import router as tts_router

router = APIRouter()

router.include_router(auth_router, tags=["auth"])
router.include_router(sessions_router, tags=["sessions"])
router.include_router(cards_router, tags=["cards", "decks", "notes"])
router.include_router(imports_router, tags=["imports"])
router.include_router(metrics_router, tags=["metrics", "events", "users"])
router.include_router(tts_router, tags=["tts"])
router.include_router(admin_router, tags=["admin"])
