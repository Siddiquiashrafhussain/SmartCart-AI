"""
SmartCart AI - Shopping Session & Cart Item API Endpoints
"""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.product import Product
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.schemas.cart import (
    SessionCreate,
    SessionResponse,
    CartItemResponse,
    CartItemUpdate,
    ScanRequest
)

router = APIRouter(prefix="/sessions", tags=["Shopping Sessions & Cart"])


def _format_session_response(session: ShoppingSession) -> SessionResponse:
    item_responses = []
    subtotal = 0.0
    total_items = 0

    for item in session.items:
        item_total = item.quantity * item.unit_price
        subtotal += item_total
        total_items += item.quantity
        item_responses.append(
            CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=round(item_total, 2)
            )
        )

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        cart_id=session.cart_id,
        status=session.status,
        started_at=session.created_at,
        completed_at=session.completed_at,
        items=item_responses,
        total_items=total_items,
        subtotal=round(subtotal, 2)
    )


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """
    Initialize a customer shopping session linked to a user and cart identifier.
    """
    new_session = ShoppingSession(
        user_id=payload.user_id,
        cart_id=payload.cart_id,
        status="ACTIVE"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    logger.info(f"Started shopping session ID={new_session.id} for user={payload.user_id}, cart={payload.cart_id}")
    return _format_session_response(new_session)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieve session details, virtual cart items, and running spend totals.
    """
    session = (
        db.query(ShoppingSession)
        .options(
            joinedload(ShoppingSession.items)
            .joinedload(CartItem.product)
            .joinedload(Product.inventory)
        )
        .filter(ShoppingSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    return _format_session_response(session)


@router.post("/scan", response_model=SessionResponse)
def scan_and_add_to_cart(payload: ScanRequest, db: Session = Depends(get_db)):
    """
    Register a barcode scan event and add/increment the product in the virtual cart.
    Executed inside a transactional boundary with idempotency safeguards.
    """
    session = (
        db.query(ShoppingSession)
        .options(joinedload(ShoppingSession.items).joinedload(CartItem.product))
        .filter(ShoppingSession.id == payload.session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {payload.session_id} not found."
        )

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add items to session in '{session.status}' status."
        )

    # Check Idempotency Key if provided
    if payload.idempotency_key:
        existing_scan = db.query(ScanEvent).filter(
            ScanEvent.idempotency_key == payload.idempotency_key
        ).first()
        if existing_scan:
            logger.info(f"Duplicate scan prevented by idempotency key: {payload.idempotency_key}")
            return _format_session_response(session)

    # Lookup Product
    product = (
        db.query(Product)
        .options(joinedload(Product.inventory))
        .filter(Product.barcode == payload.barcode.strip())
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barcode '{payload.barcode}' does not match any product in catalog."
        )

    # Record Scan Event
    scan_event = ScanEvent(
        session_id=session.id,
        product_id=product.id,
        client_timestamp=payload.client_timestamp or datetime.now(timezone.utc),
        idempotency_key=payload.idempotency_key,
        raw_payload={"barcode": payload.barcode}
    )
    db.add(scan_event)

    # Update or Add Cart Item
    cart_item = next((item for item in session.items if item.product_id == product.id), None)
    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = CartItem(
            session_id=session.id,
            product_id=product.id,
            quantity=1,
            unit_price=product.price
        )
        db.add(new_cart_item)

    db.commit()
    db.refresh(session)
    logger.info(f"Item scanned: '{product.name}' in session {session.id}")
    return _format_session_response(session)


@router.patch("/{session_id}/items/{item_id}", response_model=SessionResponse)
def update_cart_item(
    session_id: int,
    item_id: int,
    payload: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the quantity of a specific item in the virtual cart.
    If quantity is 0, the item is removed from the cart.
    """
    session = (
        db.query(ShoppingSession)
        .options(joinedload(ShoppingSession.items).joinedload(CartItem.product))
        .filter(ShoppingSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify items in a session with status '{session.status}'."
        )

    cart_item = next((item for item in session.items if item.id == item_id), None)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item {item_id} not found in session {session_id}."
        )

    if payload.quantity == 0:
        db.delete(cart_item)
        logger.info(f"Deleted cart item {item_id} from session {session_id}")
    else:
        cart_item.quantity = payload.quantity
        logger.info(f"Updated cart item {item_id} quantity to {payload.quantity} in session {session_id}")

    db.commit()
    db.refresh(session)
    return _format_session_response(session)


@router.delete("/{session_id}/items/{item_id}", response_model=SessionResponse)
def remove_cart_item(
    session_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove an item entirely from the virtual shopping cart.
    """
    session = (
        db.query(ShoppingSession)
        .options(joinedload(ShoppingSession.items).joinedload(CartItem.product))
        .filter(ShoppingSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove items from a session with status '{session.status}'."
        )

    cart_item = next((item for item in session.items if item.id == item_id), None)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item {item_id} not found in session {session_id}."
        )

    db.delete(cart_item)
    db.commit()
    db.refresh(session)
    logger.info(f"Removed cart item {item_id} from session {session_id}")
    return _format_session_response(session)
