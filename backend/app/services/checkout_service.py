"""
SmartCart AI - End-to-End Checkout & Receipt Service
Orchestrates cart validation, multi-modal verification evaluation,
tamper-evident digital receipt issuance, inventory ledger decrements,
and attendant exception review routing.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.core.websocket import ws_manager
from backend.app.models.session import ShoppingSession, CartItem
from backend.app.models.product import Product, Inventory
from backend.app.models.alert import Receipt
from backend.app.schemas.verification import CheckoutDecision
from backend.app.schemas.checkout import (
    ReceiptResponse,
    CheckoutFinalizeResponse,
    ReceiptDetailResponse
)
from backend.app.services.verification_engine import VerificationEngine


class CheckoutService:
    """
    Coordinates checkout finalization, verification policies, digital receipts,
    and attendant review workflows.
    """

    NON_MONETARY_DISCLAIMER = (
        "DEMO NOTICE: This digital receipt represents simulated checkout finalization for the "
        "SmartCart AI prototype. No actual credit card or monetary transaction has occurred."
    )

    @classmethod
    def finalize_checkout(
        cls,
        session_id: int,
        db: Session,
        idempotency_key: Optional[str] = None
    ) -> CheckoutFinalizeResponse:
        """
        Executes end-to-end checkout for a shopping session:
        1. Validates session state and cart contents.
        2. Guards against repeated checkout requests (idempotency).
        3. Evaluates evidence via VerificationEngine.
        4. If AUTO_APPROVE: finalizes session, decrements store inventory, generates digital receipt.
        5. If STAFF_REVIEW_RECOMMENDED: flags session, routes to attendant dashboard, halts auto-finalization.
        """
        # Fetch Session with items and product inventory
        session = (
            db.query(ShoppingSession)
            .options(
                joinedload(ShoppingSession.items).joinedload(CartItem.product),
                joinedload(ShoppingSession.receipt)
            )
            .filter(ShoppingSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shopping session {session_id} not found."
            )

        # 1. Idempotency Check: Already completed sessions return their existing receipt
        if session.status == "COMPLETED":
            existing_receipt = session.receipt
            if not existing_receipt:
                existing_receipt = db.query(Receipt).filter(Receipt.session_id == session.id).first()

            sanitized_user = cls._sanitize_id(session.user_id)
            logger.info(f"Idempotent checkout replay for already COMPLETED session ID={session.id} (user={sanitized_user})")

            return CheckoutFinalizeResponse(
                session_id=session.id,
                session_status="COMPLETED",
                checkout_finalized=True,
                review_required=False,
                decision=CheckoutDecision.AUTO_APPROVE.value,
                verification_outcome="NO_DISCREPANCY_DETECTED",
                confidence_score=1.0,
                reasons=["Session already finalized. Existing digital receipt returned idempotently."],
                safety_and_trust_notice="Receipt already verified and issued.",
                receipt=ReceiptResponse.model_validate(existing_receipt) if existing_receipt else None,
                is_idempotent_replay=True,
                message="Session already checked out. Digital receipt replayed."
            )

        # 2. State Validation
        if session.status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot checkout a cancelled session (ID={session_id})."
            )

        if session.status == "FLAGGED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Shopping session {session_id} is flagged for store attendant assistance. "
                    "Auto-checkout is halted until reviewed by staff."
                )
            )

        # 3. Cart Items Validation
        if not session.items or len(session.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot checkout an empty cart. Please scan merchandise before finalizing."
            )

        total_units = sum(item.quantity for item in session.items)
        if total_units <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart item quantity must be greater than zero to proceed to checkout."
            )

        # 4. Run Verification Engine
        try:
            engine = VerificationEngine(db)
            verif_result = engine.evaluate_session(session.id)
        except Exception as e:
            logger.error(f"Verification engine failure on session {session.id}: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Verification engine encountered an internal error: {str(e)}"
            )

        decision = verif_result.checkout_decision
        sanitized_user = cls._sanitize_id(session.user_id)

        # 5. Policy Decision: AUTO_APPROVE vs STAFF_REVIEW_RECOMMENDED
        if decision == CheckoutDecision.AUTO_APPROVE.value:
            # Transactional Finalization
            try:
                # Calculate financial and item totals
                subtotal = sum(item.quantity * item.unit_price for item in session.items)
                total_amount = round(subtotal, 2)

                # Generate tamper-evident transaction hash
                now_utc = datetime.now(timezone.utc)
                tx_hash = cls._generate_transaction_hash(session.id, total_amount, total_units, now_utc)

                # Create Digital Receipt
                receipt = Receipt(
                    session_id=session.id,
                    total_amount=total_amount,
                    item_count=total_units,
                    payment_status="SIMULATED_PAID",
                    transaction_hash=tx_hash
                )
                db.add(receipt)

                # Decrement Store Inventory
                for item in session.items:
                    inv = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
                    if inv:
                        inv.total_store_stock = max(0, inv.total_store_stock - item.quantity)
                        inv.estimated_visible_stock = max(0, inv.estimated_visible_stock - item.quantity)

                # Update Session Status
                session.status = "COMPLETED"
                session.completed_at = now_utc

                db.commit()
                db.refresh(receipt)
                db.refresh(session)

                logger.info(
                    f"Checkout successfully finalized for session ID={session.id} (user={sanitized_user}): "
                    f"items={total_units}, total=${total_amount:.2f}, tx_hash={tx_hash[:16]}..."
                )

                # Broadcast real-time event to staff dashboard
                ws_manager.broadcast_sync({
                    "event_type": "CHECKOUT_FINALIZED",
                    "session_id": session.id,
                    "receipt_id": receipt.id,
                    "total_amount": total_amount,
                    "item_count": total_units,
                    "timestamp": now_utc.isoformat()
                })

                return CheckoutFinalizeResponse(
                    session_id=session.id,
                    session_status="COMPLETED",
                    checkout_finalized=True,
                    review_required=False,
                    decision=decision,
                    verification_outcome=verif_result.outcome,
                    confidence_score=verif_result.confidence_score,
                    reasons=verif_result.reasons,
                    safety_and_trust_notice=verif_result.safety_and_trust_notice,
                    receipt=ReceiptResponse.model_validate(receipt),
                    is_idempotent_replay=False,
                    message="Checkout successfully finalized. Digital receipt issued."
                )

            except Exception as e:
                db.rollback()
                logger.error(f"Database error finalizing checkout for session {session.id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database transaction failure during checkout finalization: {str(e)}"
                )

        else:
            # STAFF_REVIEW_RECOMMENDED: Session is FLAGGED
            try:
                session.status = "FLAGGED"
                db.commit()
                db.refresh(session)

                logger.warning(
                    f"Checkout halted for session ID={session.id} (user={sanitized_user}): "
                    f"outcome={verif_result.outcome}, decision={decision}. Flagged for attendant review."
                )

                # Broadcast to attendant dashboard
                ws_manager.broadcast_sync({
                    "event_type": "CHECKOUT_FLAGGED",
                    "session_id": session.id,
                    "user_id": sanitized_user,
                    "outcome": verif_result.outcome,
                    "reasons": verif_result.reasons,
                    "confidence_score": verif_result.confidence_score,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

                return CheckoutFinalizeResponse(
                    session_id=session.id,
                    session_status="FLAGGED",
                    checkout_finalized=False,
                    review_required=True,
                    decision=decision,
                    verification_outcome=verif_result.outcome,
                    confidence_score=verif_result.confidence_score,
                    reasons=verif_result.reasons,
                    safety_and_trust_notice=verif_result.safety_and_trust_notice,
                    receipt=None,
                    is_idempotent_replay=False,
                    message="Checkout halted for friendly staff assistance. Store attendant notified."
                )

            except Exception as e:
                db.rollback()
                logger.error(f"Database error flagging session {session.id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database error updating session state."
                )

    @classmethod
    def staff_override_checkout(
        cls,
        session_id: int,
        staff_id: str,
        override_reason: str,
        action: str,
        db: Session
    ) -> CheckoutFinalizeResponse:
        """
        Allows authorized store attendants to resolve a FLAGGED session:
        - APPROVE_CHECKOUT: Finalizes checkout, issues receipt, and records audit note.
        - REJECT_CANCEL: Cancels the session without receipt.
        """
        session = (
            db.query(ShoppingSession)
            .options(
                joinedload(ShoppingSession.items).joinedload(CartItem.product),
                joinedload(ShoppingSession.receipt)
            )
            .filter(ShoppingSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shopping session {session_id} not found."
            )

        if session.status != "FLAGGED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only FLAGGED sessions can be overridden by staff (current status='{session.status}')."
            )

        now_utc = datetime.now(timezone.utc)
        sanitized_staff = cls._sanitize_id(staff_id)

        if action == "APPROVE_CHECKOUT":
            try:
                subtotal = sum(item.quantity * item.unit_price for item in session.items)
                total_amount = round(subtotal, 2)
                total_units = sum(item.quantity for item in session.items)

                tx_hash = cls._generate_transaction_hash(session.id, total_amount, total_units, now_utc, salt=staff_id)

                receipt = Receipt(
                    session_id=session.id,
                    total_amount=total_amount,
                    item_count=total_units,
                    payment_status="SIMULATED_PAID",
                    transaction_hash=tx_hash
                )
                db.add(receipt)

                for item in session.items:
                    inv = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
                    if inv:
                        inv.total_store_stock = max(0, inv.total_store_stock - item.quantity)
                        inv.estimated_visible_stock = max(0, inv.estimated_visible_stock - item.quantity)

                session.status = "COMPLETED"
                session.completed_at = now_utc

                db.commit()
                db.refresh(receipt)
                db.refresh(session)

                logger.info(
                    f"Staff override APPROVE executed on session ID={session.id} by staff={sanitized_staff}: "
                    f"reason='{override_reason}'"
                )

                ws_manager.broadcast_sync({
                    "event_type": "CHECKOUT_OVERRIDDEN",
                    "session_id": session.id,
                    "staff_id": sanitized_staff,
                    "override_reason": override_reason,
                    "receipt_id": receipt.id,
                    "timestamp": now_utc.isoformat()
                })

                return CheckoutFinalizeResponse(
                    session_id=session.id,
                    session_status="COMPLETED",
                    checkout_finalized=True,
                    review_required=False,
                    decision="STAFF_OVERRIDE_APPROVED",
                    verification_outcome="OVERRIDDEN_BY_STAFF",
                    confidence_score=1.0,
                    reasons=[f"Attendant override ({sanitized_staff}): {override_reason}"],
                    safety_and_trust_notice="Approved by store attendant.",
                    receipt=ReceiptResponse.model_validate(receipt),
                    is_idempotent_replay=False,
                    message="Session approved by store attendant. Digital receipt issued."
                )

            except Exception as e:
                db.rollback()
                logger.error(f"Database error in staff override for session {session.id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Staff override failed: {str(e)}"
                )

        elif action == "REJECT_CANCEL":
            try:
                session.status = "CANCELLED"
                session.completed_at = now_utc
                db.commit()
                db.refresh(session)

                logger.info(
                    f"Staff override CANCEL executed on session ID={session.id} by staff={sanitized_staff}: "
                    f"reason='{override_reason}'"
                )

                ws_manager.broadcast_sync({
                    "event_type": "CHECKOUT_CANCELLED",
                    "session_id": session.id,
                    "staff_id": sanitized_staff,
                    "override_reason": override_reason,
                    "timestamp": now_utc.isoformat()
                })

                return CheckoutFinalizeResponse(
                    session_id=session.id,
                    session_status="CANCELLED",
                    checkout_finalized=False,
                    review_required=False,
                    decision="STAFF_OVERRIDE_CANCELLED",
                    verification_outcome="CANCELLED_BY_STAFF",
                    confidence_score=0.0,
                    reasons=[f"Attendant cancellation ({sanitized_staff}): {override_reason}"],
                    safety_and_trust_notice="Session cancelled by store staff.",
                    receipt=None,
                    is_idempotent_replay=False,
                    message="Shopping session cancelled by store attendant."
                )
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database error cancelling session."
                )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid staff override action '{action}'. Must be 'APPROVE_CHECKOUT' or 'REJECT_CANCEL'."
            )

    @classmethod
    def get_receipt(cls, session_id: int, db: Session) -> ReceiptDetailResponse:
        """
        Retrieves receipt details and item breakdown for customer display.
        """
        session = (
            db.query(ShoppingSession)
            .options(
                joinedload(ShoppingSession.items).joinedload(CartItem.product),
                joinedload(ShoppingSession.receipt)
            )
            .filter(ShoppingSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shopping session {session_id} not found."
            )

        if not session.receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No receipt issued for session {session_id}. Session status is '{session.status}'."
            )

        receipt = session.receipt
        items_breakdown = [
            {
                "product_name": item.product.name,
                "sku": item.product.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": round(item.quantity * item.unit_price, 2)
            }
            for item in session.items
        ]

        subtotal = round(receipt.total_amount, 2)
        tax = round(subtotal * 0.0825, 2)  # Demo 8.25% tax computation
        grand_total = round(subtotal + tax, 2)

        return ReceiptDetailResponse(
            receipt=ReceiptResponse.model_validate(receipt),
            session_id=session.id,
            user_id=cls._sanitize_id(session.user_id),
            cart_id=session.cart_id,
            item_count=receipt.item_count,
            subtotal=subtotal,
            tax=tax,
            grand_total=grand_total,
            items=items_breakdown,
            disclaimer=cls.NON_MONETARY_DISCLAIMER
        )

    @staticmethod
    def _generate_transaction_hash(session_id: int, total: float, count: int, timestamp: datetime, salt: str = "") -> str:
        """
        Generates a SHA-256 tamper-evident cryptographic hash for the digital receipt.
        """
        seed = f"SMARTCART:{session_id}:{total:.2f}:{count}:{timestamp.isoformat()}:{salt}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    @staticmethod
    def _sanitize_id(identifier: Optional[str]) -> str:
        """
        Masks customer identifiers for privacy-compliant logging and receipt display.
        """
        if not identifier:
            return "anon_user"
        if len(identifier) <= 4:
            return identifier[0] + "***"
        return identifier[:3] + "***" + identifier[-2:]
