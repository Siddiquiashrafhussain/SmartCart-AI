"""
SmartCart AI - Restocking Alerts & Inventory Intelligence Pydantic Schemas
Defines request and response schemas for shelf observation evaluation,
alert tracking, deduplication, and attendant resolution workflows.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RestockAlertResponse(BaseModel):
    id: int
    shelf_id: int
    product_id: int
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    shelf_bay_code: Optional[str] = None
    alert_type: str = Field(..., description="LOW_STOCK, STOCKOUT, MISPLACED_ITEM, UNSCANNED_PICKUP")
    observed_count: int
    threshold: int
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    evidence_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ShelfObservationEvaluateRequest(BaseModel):
    shelf_id: int = Field(..., ge=1, description="Target shelf bay ID")
    observations: Dict[str, int] = Field(..., description="Observed class counts e.g. {'cereal': 1, 'milk': 0}")
    audit_id: Optional[str] = Field(default=None, description="Optional UUID of the computer vision audit")
    evidence_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Detection metadata, confidence scores")


class ShelfEvaluationResponse(BaseModel):
    shelf_id: int
    total_observations: int
    alerts_created: int
    alerts_updated: int
    alerts: List[RestockAlertResponse]
    unmapped_classes: List[str]
    summary: str


class AlertResolveRequest(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=255, description="Attendant restock note")
    units_restocked: Optional[int] = Field(default=None, ge=1, description="Quantity replenished to shelf")


class AlertsSummaryStatsResponse(BaseModel):
    total_active_alerts: int
    active_stockouts: int
    active_low_stock: int
    total_resolved_alerts: int
