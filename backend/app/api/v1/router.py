"""
SmartCart AI - API v1 Master Router
"""

from fastapi import APIRouter
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.sessions import router as sessions_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.verification import router as verification_router
from backend.app.api.v1.vision import router as vision_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.ws import router as ws_router

api_v1_router = APIRouter()

api_v1_router.include_router(products_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(sessions_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(verification_router)
api_v1_router.include_router(vision_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(ws_router)
