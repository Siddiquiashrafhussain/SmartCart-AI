"""
SmartCart AI - Models Manifest
Import all models so that Base.metadata recognizes all relational tables.
"""

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.product import Product, Inventory
from backend.app.models.shelf import Shelf, Planogram
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.models.verification import SensorEvent, ShelfPickupEvent, VerificationEvent
from backend.app.models.alert import RestockAlert, Receipt

__all__ = [
    "Base",
    "TimestampMixin",
    "Product",
    "Inventory",
    "Shelf",
    "Planogram",
    "ShoppingSession",
    "CartItem",
    "ScanEvent",
    "SensorEvent",
    "ShelfPickupEvent",
    "VerificationEvent",
    "RestockAlert",
    "Receipt",
]
