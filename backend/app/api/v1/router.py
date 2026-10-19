"""
SmartCart AI - API v1 Master Router
"""

from fastapi import APIRouter
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.sessions import router as sessions_router

api_v1_router = APIRouter()

api_v1_router.include_router(products_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(sessions_router)
