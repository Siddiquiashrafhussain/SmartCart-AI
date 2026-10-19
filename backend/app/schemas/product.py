"""
SmartCart AI - Product and Inventory Pydantic Validation Schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class InventoryBase(BaseModel):
    total_store_stock: int = Field(default=0, ge=0, description="Total store inventory including backroom")
    estimated_visible_stock: int = Field(default=0, ge=0, description="Observed visible stock on shelf")
    safety_threshold: int = Field(default=2, ge=0, description="Restock threshold")


class InventoryUpdate(BaseModel):
    total_store_stock: Optional[int] = Field(default=None, ge=0)
    estimated_visible_stock: Optional[int] = Field(default=None, ge=0)
    safety_threshold: Optional[int] = Field(default=None, ge=0)


class InventoryResponse(InventoryBase):
    id: int
    product_id: int
    last_audited_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=64, description="Stock Keeping Unit identifier")
    barcode: str = Field(..., min_length=4, max_length=64, description="EAN-13, UPC, or QR barcode")
    name: str = Field(..., min_length=1, max_length=255, description="Product commercial name")
    category: str = Field(..., min_length=1, max_length=64, description="Product category for YOLO matching")
    price: float = Field(..., gt=0.0, description="Retail unit price")
    tare_weight_g: float = Field(..., gt=0.0, description="Tare weight in grams for scale correlation")
    description: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=255)


class ProductCreate(ProductBase):
    initial_total_stock: int = Field(default=10, ge=0, description="Initial total inventory quantity")
    initial_visible_stock: int = Field(default=4, ge=0, description="Initial visible shelf count")
    safety_threshold: int = Field(default=2, ge=0, description="Minimum restock threshold")


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, min_length=1, max_length=64)
    price: Optional[float] = Field(default=None, gt=0.0)
    tare_weight_g: Optional[float] = Field(default=None, gt=0.0)
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    inventory: Optional[InventoryResponse] = None

    model_config = ConfigDict(from_attributes=True)
