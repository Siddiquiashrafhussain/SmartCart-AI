"""
SmartCart AI - Checkout, Verification Decisions & Digital Receipts API Endpoints
Provides endpoints to finalize checkout sessions, evaluate verification outcomes,
retrieve tamper-evident digital receipts, and execute attendant review overrides.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.checkout import (
    CheckoutFinalizeRequest,
    CheckoutFinalizeResponse,
    StaffReviewOverrideRequest,
    ReceiptDetailResponse
)
from backend.app.services.checkout_service import CheckoutService

router = APIRouter(prefix="/checkout", tags=["Checkout & Digital Receipts"])


@router.post("/finalize/{session_id}", response_model=CheckoutFinalizeResponse)
def finalize_checkout(
    session_id: int,
    payload: CheckoutFinalizeRequest = CheckoutFinalizeRequest(),
    db: Session = Depends(get_db)
):
    """
    Finalize shopping session checkout:
    1. Validates virtual cart items and quantities.
    2. Runs multi-modal verification engine across scan, pickup, and weight telemetry.
    3. Applies checkout policy:
       - AUTO_APPROVE: Issues digital receipt, decrements store inventory, marks session COMPLETED.
       - STAFF_REVIEW_RECOMMENDED: Flags session for attendant assistance, halts automated checkout.
    4. Guards against duplicate charges with idempotent replay.
    """
    return CheckoutService.finalize_checkout(
        session_id=session_id,
        db=db,
        idempotency_key=payload.idempotency_key
    )


@router.post("/staff-override/{session_id}", response_model=CheckoutFinalizeResponse)
def staff_override_checkout(
    session_id: int,
    payload: StaffReviewOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Store attendant override for FLAGGED shopping sessions.
    Allows staff to manually inspect cart contents and approve checkout or cancel session.
    """
    return CheckoutService.staff_override_checkout(
        session_id=session_id,
        staff_id=payload.staff_id,
        override_reason=payload.override_reason,
        action=payload.action,
        db=db
    )


@router.get("/receipt/{session_id}", response_model=ReceiptDetailResponse)
def get_receipt(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve customer digital receipt, itemized breakdown, and tamper-evident transaction hash.
    """
    return CheckoutService.get_receipt(session_id=session_id, db=db)
