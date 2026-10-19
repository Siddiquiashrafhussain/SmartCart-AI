"""
SmartCart AI - Multi-Modal Event Ingestion & Telemetry Pydantic Schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ScanEventIngest(BaseModel):
    session_id: int = Field(..., ge=1, description="Active shopping session ID")
    barcode: str = Field(..., min_length=4, max_length=64, description="Scanned barcode string")
    quantity: int = Field(default=1, ge=1, le=50, description="Quantity scanned")
    timestamp: Optional[datetime] = Field(default=None, description="Event generation timestamp (UTC)")
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="Unique client deduplication UUID")
    is_simulated: bool = Field(default=False, description="Flag indicating simulated test event")


class ScanEventResponse(BaseModel):
    id: int
    session_id: int
    product_id: int
    quantity: int
    client_timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    is_simulated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PickupEventIngest(BaseModel):
    shelf_id: int = Field(..., ge=1, description="Observed shelf bay ID")
    detected_class: str = Field(..., min_length=1, max_length=64, description="YOLO detected class name")
    product_id: Optional[int] = Field(default=None, description="Resolved product ID if known")
    quantity_removed: int = Field(default=1, ge=1, le=50, description="Observed units removed from shelf")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Computer vision detection confidence")
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp (UTC)")
    is_simulated: bool = Field(default=False, description="Flag indicating simulated test event")
    raw_metadata: Optional[Dict[str, Any]] = None


class PickupEventResponse(BaseModel):
    id: int
    shelf_id: int
    product_id: Optional[int] = None
    detected_class: str
    confidence: float
    quantity_removed: int
    timestamp: datetime
    is_simulated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorEventIngest(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=64, description="Hardware or simulated sensor ID")
    sensor_type: str = Field(default="WEIGHT_SHELF", description="WEIGHT_SHELF or WEIGHT_CART")
    delta_weight_g: float = Field(..., description="Weight change in grams (negative for shelf removal)")
    session_id: Optional[int] = Field(default=None, description="Linked session ID if cart scale")
    shelf_id: Optional[int] = Field(default=None, description="Linked shelf bay ID if shelf scale")
    timestamp: Optional[datetime] = Field(default=None, description="Sensor measurement timestamp (UTC)")
    is_simulated: bool = Field(default=False, description="Flag indicating simulated test event")
    raw_telemetry: Optional[Dict[str, Any]] = None


class SensorEventResponse(BaseModel):
    id: int
    sensor_id: str
    sensor_type: str
    delta_weight_g: float
    session_id: Optional[int] = None
    shelf_id: Optional[int] = None
    timestamp: datetime
    is_simulated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChronologicalEventItem(BaseModel):
    event_type: str  # "SCAN", "PICKUP", "SENSOR"
    event_id: int
    timestamp: datetime
    is_simulated: bool
    summary: str
    details: Dict[str, Any]


class SessionTimelineResponse(BaseModel):
    session_id: int
    total_events: int
    timeline: List[ChronologicalEventItem]
