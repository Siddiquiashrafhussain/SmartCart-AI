"""
SmartCart AI - Inventory Management & Stock Tracking API Endpoints
"""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.product import Inventory, Product
from backend.app.schemas.product import InventoryResponse, InventoryUpdate

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=List[InventoryResponse])
def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all store inventory records, including total store stock and visible shelf estimates.
    """
    records = db.query(Inventory).offset(skip).limit(limit).all()
    return records


@router.get("/alerts/low-stock", response_model=List[InventoryResponse])
def get_low_stock_alerts(db: Session = Depends(get_db)):
    """
    Query all inventory items where estimated visible shelf stock
    falls at or below the configured safety threshold.
    """
    low_stock = (
        db.query(Inventory)
        .filter(Inventory.estimated_visible_stock <= Inventory.safety_threshold)
        .all()
    )
    logger.info(f"Retrieved {len(low_stock)} low-stock inventory records")
    return low_stock


@router.get("/alerts/stockouts", response_model=List[InventoryResponse])
def get_stockout_alerts(db: Session = Depends(get_db)):
    """
    Query all inventory items where estimated visible shelf stock is completely depleted (count == 0).
    """
    stockouts = (
        db.query(Inventory)
        .filter(Inventory.estimated_visible_stock == 0)
        .all()
    )
    logger.info(f"Retrieved {len(stockouts)} stockout inventory records")
    return stockouts


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory_by_product_id(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve inventory record for a specific product ID.
    """
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product ID {product_id} not found."
        )
    return inv


@router.patch("/{product_id}", response_model=InventoryResponse)
def update_inventory(
    product_id: int,
    payload: InventoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update inventory quantities (e.g. following visual shelf auditing or replenishment).
    """
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product ID {product_id} not found."
        )

    if payload.total_store_stock is not None:
        inv.total_store_stock = payload.total_store_stock
    if payload.estimated_visible_stock is not None:
        inv.estimated_visible_stock = payload.estimated_visible_stock
        inv.last_audited_at = datetime.now(timezone.utc)
    if payload.safety_threshold is not None:
        inv.safety_threshold = payload.safety_threshold

    db.commit()
    db.refresh(inv)
    logger.info(f"Updated inventory for product ID {product_id}: visible={inv.estimated_visible_stock}, total={inv.total_store_stock}")
    return inv
