"""
SmartCart AI - Verification Engine Pydantic Schemas
Defines request, response, audit trail, and rule configuration models.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class VerificationOutcome(str, Enum):
    NO_DISCREPANCY_DETECTED = "NO_DISCREPANCY_DETECTED"
    POTENTIAL_DISCREPANCY = "POTENTIAL_DISCREPANCY"
    INCONCLUSIVE = "INCONCLUSIVE"


class CheckoutDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    STAFF_REVIEW_RECOMMENDED = "STAFF_REVIEW_RECOMMENDED"


class EventReferenceItem(BaseModel):
    event_type: str = Field(..., description="SCAN, PICKUP, or SENSOR")
    event_id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    timestamp: datetime
    confidence: Optional[float] = None
    is_simulated: bool
    summary: str


class RuleEvaluationDetail(BaseModel):
    rule_name: str
    status: str  # PASSED, FAILED, INCONCLUSIVE, SKIPPED
    explanation: str
    confidence_impact: float = 0.0
    evidence_ids: List[int] = Field(default_factory=list)


class VerificationResultResponse(BaseModel):
    verification_id: str
    session_id: int
    outcome: VerificationOutcome
    verdict: str  # Backwards-compatible (CONSISTENT, UNCERTAIN, MISMATCH)
    checkout_decision: CheckoutDecision
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    staff_review_recommended: bool
    is_simulated: bool
    reasons: List[str]
    safety_and_trust_notice: str
    relevant_event_references: List[EventReferenceItem]
    rule_evaluations: List[RuleEvaluationDetail]
    session_items_count: int
    scans_count: int
    pickups_count: int
    sensor_events_count: int
    evaluated_at: datetime
    audit_trail: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class VerificationRulesConfigResponse(BaseModel):
    correlation_window_seconds: float
    weight_tolerance_grams: float
    min_verification_confidence: float
    allow_inconclusive_checkout_bypass: bool
    configured_rules: List[Dict[str, Any]]
