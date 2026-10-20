"""
SmartCart AI - Restocking Alerts & Inventory Intelligence API Endpoints
Exposes endpoints for processing visual shelf counts, querying active alerts,
and executing store attendant resolution workflows.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.schemas.alert import (
    RestockAlertResponse,
    ShelfObservationEvaluateRequest,
    ShelfEvaluationResponse,
    AlertResolveRequest,
    AlertsSummaryStatsResponse,
)
from backend.app.services.alert_service import InventoryAlertService

router = APIRouter(prefix="/alerts", tags=["Inventory Intelligence & Restocking Alerts"])


@router.post("/evaluate-shelf", response_model=ShelfEvaluationResponse)
def evaluate_shelf_observations(
    payload: ShelfObservationEvaluateRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate visible item counts observed on a shelf bay against configured inventory thresholds.
    Triggers LOW_STOCK or STOCKOUT alerts with automatic deduplication.
    Updates estimated visible shelf stock while keeping total store inventory intact.
    """
    service = InventoryAlertService(db)
    try:
        response = service.evaluate_shelf_observations(
            shelf_id=payload.shelf_id,
            observations=payload.observations,
            audit_id=payload.audit_id,
            evidence_metadata=payload.evidence_metadata
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error evaluating shelf observations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate shelf observations: {str(e)}"
        )


@router.get("", response_model=List[RestockAlertResponse])
def list_alerts(
    shelf_id: Optional[int] = Query(None, description="Filter by shelf bay ID"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (e.g. LOW_STOCK, STOCKOUT)"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List restocking and inventory alerts with optional filtering and pagination.
    """
    service = InventoryAlertService(db)
    return service.list_alerts(
        shelf_id=shelf_id,
        product_id=product_id,
        alert_type=alert_type,
        is_resolved=is_resolved,
        skip=skip,
        limit=limit
    )


@router.get("/stats/summary", response_model=AlertsSummaryStatsResponse)
def get_alerts_summary(db: Session = Depends(get_db)):
    """
    Retrieve store-wide summary metrics on active restock alerts, stockouts, and resolved tasks.
    """
    service = InventoryAlertService(db)
    return service.get_summary_stats()


@router.get("/{alert_id}", response_model=RestockAlertResponse)
def get_alert_by_id(alert_id: int, db: Session = Depends(get_db)):
    """
    Retrieve full details and evidence metadata for a specific restock alert.
    """
    service = InventoryAlertService(db)
    try:
        return service.get_alert_by_id(alert_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.patch("/{alert_id}/resolve", response_model=RestockAlertResponse)
def resolve_alert(
    alert_id: int,
    payload: AlertResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Store attendant resolution workflow: Mark an alert as resolved and optionally
    record replenishment count to update visible shelf inventory.
    """
    service = InventoryAlertService(db)
    try:
        return service.resolve_alert(
            alert_id=alert_id,
            resolution_note=payload.resolution_note,
            units_restocked=payload.units_restocked
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
