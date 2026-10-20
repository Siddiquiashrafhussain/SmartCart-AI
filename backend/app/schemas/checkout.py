"""
SmartCart AI - Checkout, Receipts, and Staff Review Schemas
Pydantic contracts for session finalization, verification outcomes,
tamper-evident digital receipts, and attendant override audits.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ReceiptResponse(BaseModel):
    id: int
    session_id: int
    total_amount: float
    item_count: int
    payment_status: str = Field(..., description="e.g. SIMULATED_PAID (non-monetary demo)")
    transaction_hash: str = Field(..., description="SHA-256 cryptographic audit signature")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckoutFinalizeRequest(BaseModel):
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="Optional client UUID")


class CheckoutFinalizeResponse(BaseModel):
    session_id: int
    session_status: str = Field(..., description="COMPLETED, FLAGGED, or ACTIVE")
    checkout_finalized: bool
    review_required: bool
    decision: str = Field(..., description="AUTO_APPROVE or STAFF_REVIEW_RECOMMENDED")
    verification_outcome: str = Field(..., description="NO_DISCREPANCY_DETECTED, POTENTIAL_DISCREPANCY, or INCONCLUSIVE")
    confidence_score: float
    reasons: List[str]
    safety_and_trust_notice: str
    receipt: Optional[ReceiptResponse] = None
    is_idempotent_replay: bool = False
    message: str


class StaffReviewOverrideRequest(BaseModel):
    staff_id: str = Field(..., min_length=2, max_length=64, description="Attendant badge or staff ID")
    override_reason: str = Field(..., min_length=3, max_length=255, description="Clear justification note")
    action: str = Field(default="APPROVE_CHECKOUT", description="APPROVE_CHECKOUT or REJECT_CANCEL")


class ReceiptDetailResponse(BaseModel):
    receipt: ReceiptResponse
    session_id: int
    user_id: str
    cart_id: str
    item_count: int
    subtotal: float
    tax: float
    grand_total: float
    items: List[dict]
    disclaimer: str
