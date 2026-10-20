"""
SmartCart AI - Verification Engine API Endpoints
Exposes endpoints for running multi-modal checkout verification, querying audit trails,
and inspecting active rules.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.session import ShoppingSession
from backend.app.models.verification import VerificationEvent
from backend.app.schemas.verification import (
    VerificationResultResponse,
    VerificationRulesConfigResponse,
)
from backend.app.services.verification_engine import VerificationEngine

router = APIRouter(prefix="/verification", tags=["Checkout Verification Engine"])


@router.post("/verify/{session_id}", response_model=VerificationResultResponse)
def verify_session(session_id: int, db: Session = Depends(get_db)):
    """
    Run the multi-modal verification engine for an active or checking-out shopping session.
    Correlates barcode scans, camera shelf pickups, load-cells, and catalog weights.
    Persists structured audit trail and updates session checkout status.
    """
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    engine = VerificationEngine(db)
    result = engine.evaluate_session(session_id)
    return result


@router.get("/rules", response_model=VerificationRulesConfigResponse)
def get_verification_rules(db: Session = Depends(get_db)):
    """
    Retrieve active configurable verification rules, correlation windows, and tolerances.
    """
    engine = VerificationEngine(db)
    return VerificationRulesConfigResponse(
        correlation_window_seconds=settings.CORRELATION_WINDOW_SECONDS,
        weight_tolerance_grams=settings.WEIGHT_TOLERANCE_GRAMS,
        min_verification_confidence=settings.MIN_VERIFICATION_CONFIDENCE,
        allow_inconclusive_checkout_bypass=settings.ALLOW_INCONCLUSIVE_CHECKOUT_BYPASS,
        configured_rules=engine.get_configured_rules()
    )


@router.get("/session/{session_id}", response_model=VerificationResultResponse)
def get_latest_session_verification(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the most recent verification audit record for a given shopping session.
    """
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping session {session_id} not found."
        )

    verif = (
        db.query(VerificationEvent)
        .filter(VerificationEvent.session_id == session_id)
        .order_by(VerificationEvent.id.desc())
        .first()
    )

    if not verif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification record exists yet for session {session_id}."
        )

    engine = VerificationEngine(db)
    return engine._build_response_from_model(verif, session)


@router.get("/{verification_id}", response_model=VerificationResultResponse)
def get_verification_by_id(verification_id: str, db: Session = Depends(get_db)):
    """
    Retrieve structured verification audit trail by unique verification UUID.
    """
    verif = db.query(VerificationEvent).filter(VerificationEvent.verification_id == verification_id).first()
    if not verif and verification_id.isdigit():
        verif = db.query(VerificationEvent).filter(VerificationEvent.id == int(verification_id)).first()

    if not verif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record with ID '{verification_id}' not found."
        )

    session = db.query(ShoppingSession).filter(ShoppingSession.id == verif.session_id).first()
    engine = VerificationEngine(db)
    return engine._build_response_from_model(verif, session)
