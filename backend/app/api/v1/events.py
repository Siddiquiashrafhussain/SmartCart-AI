"""
SmartCart AI - Multi-Modal Event Ingestion API Endpoints
Handles Barcode Scans, Vision Shelf Pickups, and Sensor Weight Deltas.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.product import Product
from backend.app.models.shelf import Shelf
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.models.verification import SensorEvent, ShelfPickupEvent
from backend.app.schemas.events import (
    ScanEventIngest,
    ScanEventResponse,
    PickupEventIngest,
    PickupEventResponse,
    SensorEventIngest,
    SensorEventResponse,
    SessionTimelineResponse,
    ChronologicalEventItem,
)

router = APIRouter(prefix="/events", tags=["Event Ingestion & Telemetry"])


@router.post("/scan", response_model=ScanEventResponse, status_code=status.HTTP_201_CREATED)
def ingest_scan_event(payload: ScanEventIngest, db: Session = Depends(get_db)):
    """
    Ingest a barcode scan event.
    Validates session state, performs deduplication, and transactionally updates cart.
    """
    # 1. Validate Session
    session = db.query(ShoppingSession).filter(ShoppingSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {payload.session_id} not found."
        )
    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot ingest scan for session in '{session.status}' state."
        )

    # 2. Idempotency Deduplication Check
    if payload.idempotency_key:
        existing_event = db.query(ScanEvent).filter(
            ScanEvent.idempotency_key == payload.idempotency_key
        ).first()
        if existing_event:
            logger.info(f"Duplicate scan event dropped via idempotency key: {payload.idempotency_key}")
            return existing_event

    # 3. Resolve Product
    clean_barcode = payload.barcode.strip()
    product = db.query(Product).filter(Product.barcode == clean_barcode).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barcode '{clean_barcode}' does not exist in store catalogue."
        )

    # 4. Record Scan Event
    event_timestamp = payload.timestamp or datetime.now(timezone.utc)
    scan_event = ScanEvent(
        session_id=session.id,
        product_id=product.id,
        quantity=payload.quantity,
        client_timestamp=event_timestamp,
        idempotency_key=payload.idempotency_key,
        is_simulated=payload.is_simulated,
        raw_payload={"barcode": clean_barcode, "simulated": payload.is_simulated}
    )
    db.add(scan_event)

    # 5. Transactionally Update Cart
    cart_item = db.query(CartItem).filter(
        CartItem.session_id == session.id,
        CartItem.product_id == product.id
    ).first()

    if cart_item:
        cart_item.quantity += payload.quantity
    else:
        new_item = CartItem(
            session_id=session.id,
            product_id=product.id,
            quantity=payload.quantity,
            unit_price=product.price
        )
        db.add(new_item)

    db.commit()
    db.refresh(scan_event)
    logger.info(f"Ingested scan event ID={scan_event.id} (simulated={payload.is_simulated})")
    return scan_event


@router.post("/pickup", response_model=PickupEventResponse, status_code=status.HTTP_201_CREATED)
def ingest_pickup_event(payload: PickupEventIngest, db: Session = Depends(get_db)):
    """
    Ingest a vision-derived shelf pickup event (item removed from shelf bay).
    """
    # Verify shelf exists
    shelf = db.query(Shelf).filter(Shelf.id == payload.shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelf ID {payload.shelf_id} not found."
        )

    # Resolve product if not provided
    product_id = payload.product_id
    if not product_id:
        product = db.query(Product).filter(Product.category.ilike(f"%{payload.detected_class}%")).first()
        if product:
            product_id = product.id

    event_timestamp = payload.timestamp or datetime.now(timezone.utc)
    pickup_event = ShelfPickupEvent(
        shelf_id=payload.shelf_id,
        product_id=product_id,
        detected_class=payload.detected_class,
        confidence=payload.confidence,
        quantity_removed=payload.quantity_removed,
        timestamp=event_timestamp,
        is_simulated=payload.is_simulated,
        raw_metadata=payload.raw_metadata
    )
    db.add(pickup_event)
    db.commit()
    db.refresh(pickup_event)

    logger.info(f"Ingested shelf pickup event ID={pickup_event.id} on shelf {payload.shelf_id} (class={payload.detected_class}, simulated={payload.is_simulated})")
    return pickup_event


@router.post("/sensor", response_model=SensorEventResponse, status_code=status.HTTP_201_CREATED)
def ingest_sensor_event(payload: SensorEventIngest, db: Session = Depends(get_db)):
    """
    Ingest a load-cell weight delta telemetry event.
    """
    event_timestamp = payload.timestamp or datetime.now(timezone.utc)
    sensor_event = SensorEvent(
        sensor_id=payload.sensor_id,
        sensor_type=payload.sensor_type,
        delta_weight_g=payload.delta_weight_g,
        session_id=payload.session_id,
        shelf_id=payload.shelf_id,
        timestamp=event_timestamp,
        is_simulated=payload.is_simulated,
        raw_telemetry=payload.raw_telemetry
    )
    db.add(sensor_event)
    db.commit()
    db.refresh(sensor_event)

    logger.info(f"Ingested sensor event ID={sensor_event.id}: delta={payload.delta_weight_g}g (simulated={payload.is_simulated})")
    return sensor_event


@router.get("/sessions/{session_id}/timeline", response_model=SessionTimelineResponse)
def get_session_event_timeline(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieve unified chronological timeline of all scan, pickup, and sensor events.
    Sorted strictly by measurement/client timestamp (not arrival order).
    """
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    # 1. Fetch Scan Events
    scans = db.query(ScanEvent).filter(ScanEvent.session_id == session_id).all()

    # 2. Fetch Sensor Events linked to session
    sensors = db.query(SensorEvent).filter(SensorEvent.session_id == session_id).all()

    # 3. Fetch Shelf Pickups occurred within session active duration
    start_time = session.created_at
    pickups = db.query(ShelfPickupEvent).filter(ShelfPickupEvent.timestamp >= start_time).all()

    # Assemble timeline items
    timeline_items: List[ChronologicalEventItem] = []

    for s in scans:
        t = s.client_timestamp or s.created_at
        timeline_items.append(
            ChronologicalEventItem(
                event_type="SCAN",
                event_id=s.id,
                timestamp=t,
                is_simulated=s.is_simulated,
                summary=f"Barcode scanned (Product ID: {s.product_id}, Qty: {s.quantity})",
                details={"product_id": s.product_id, "quantity": s.quantity, "idempotency_key": s.idempotency_key}
            )
        )

    for w in sensors:
        timeline_items.append(
            ChronologicalEventItem(
                event_type="SENSOR",
                event_id=w.id,
                timestamp=w.timestamp,
                is_simulated=w.is_simulated,
                summary=f"Weight change: {w.delta_weight_g:+.1f}g ({w.sensor_type})",
                details={"sensor_id": w.sensor_id, "delta_weight_g": w.delta_weight_g}
            )
        )

    for p in pickups:
        timeline_items.append(
            ChronologicalEventItem(
                event_type="PICKUP",
                event_id=p.id,
                timestamp=p.timestamp,
                is_simulated=p.is_simulated,
                summary=f"Camera observed pickup: {p.detected_class} on Shelf {p.shelf_id}",
                details={"shelf_id": p.shelf_id, "detected_class": p.detected_class, "confidence": p.confidence}
            )
        )

    # Sort strictly by timestamp (chronological order)
    timeline_items.sort(key=lambda x: x.timestamp)

    return SessionTimelineResponse(
        session_id=session_id,
        total_events=len(timeline_items),
        timeline=timeline_items
    )
