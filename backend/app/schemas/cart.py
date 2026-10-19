"""
SmartCart AI - Cart & Session Pydantic Validation Schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.product import ProductResponse


class SessionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64, description="Unique user or device ID")
    cart_id: str = Field(..., min_length=1, max_length=64, description="SmartCart hardware identifier")


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product: ProductResponse
    quantity: int
    unit_price: float
    total_price: float

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: int
    user_id: str
    cart_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    items: List[CartItemResponse] = Field(default_factory=list)
    total_items: int = 0
    subtotal: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class ScanRequest(BaseModel):
    session_id: int = Field(..., ge=1, description="Active shopping session ID")
    barcode: str = Field(..., min_length=4, max_length=64, description="Scanned barcode string")
    client_timestamp: Optional[datetime] = Field(default=None, description="Client device scan timestamp")
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="UUID preventing duplicate charges")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0, description="Updated quantity (0 deletes item)")
