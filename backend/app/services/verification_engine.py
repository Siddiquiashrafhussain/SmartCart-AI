"""
SmartCart AI - Modular Multi-Modal Verification Engine
Evaluates shopping sessions against multi-modal evidence (barcode scans, camera pickups, load-cells).
Distinguishes between missing evidence and contradictory evidence.
Ensures explainable, deterministic results and idempotent persistence.
"""

import uuid
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.models.verification import SensorEvent, ShelfPickupEvent, VerificationEvent
from backend.app.models.product import Product
from backend.app.schemas.verification import (
    VerificationOutcome,
    CheckoutDecision,
    EventReferenceItem,
    RuleEvaluationDetail,
    VerificationResultResponse,
)
from backend.app.services.checkout_decision import CheckoutDecisionService


class VerificationEngine:
    """
    Principal event-correlation and verification engine for SmartCart AI.
    """

    def __init__(self, db: Session):
        self.db = db
        self.correlation_window = settings.CORRELATION_WINDOW_SECONDS
        self.weight_tolerance = settings.WEIGHT_TOLERANCE_GRAMS
        self.min_confidence = settings.MIN_VERIFICATION_CONFIDENCE

    def get_configured_rules(self) -> List[Dict[str, Any]]:
        """Return list of active configurable verification rules."""
        return [
            {
                "rule_name": "RULE_CART_SCAN_CONSISTENCY",
                "description": "Validates that virtual cart item quantities exactly match confirmed barcode scan events.",
                "type": "INTEGRITY",
                "weight": 0.25,
            },
            {
                "rule_name": "RULE_VISION_PICKUP_CORRELATION",
                "description": "Correlates camera shelf pickup events with barcode scans within synchronization window tau.",
                "type": "MULTI_MODAL",
                "weight": 0.35,
            },
            {
                "rule_name": "RULE_WEIGHT_TELEMETRY_CORRELATION",
                "description": "Checks shelf scale drops and cart scale increases against catalogue product tare weights.",
                "type": "SENSOR",
                "weight": 0.25,
            },
            {
                "rule_name": "RULE_TEMPORAL_SYNCHRONIZATION",
                "description": "Validates that correlated physical events occurred within correlation window tau.",
                "type": "TEMPORAL",
                "weight": 0.15,
            },
        ]

    def _compute_session_evidence_fingerprint(
        self,
        session: ShoppingSession,
        scans: List[ScanEvent],
        pickups: List[ShelfPickupEvent],
        sensors: List[SensorEvent]
    ) -> str:
        """
        Computes a deterministic hash of all session items and evidence events.
        Enables idempotent verification runs.
        """
        fingerprint_data = {
            "session_id": session.id,
            "cart_items": sorted(
                [(item.product_id, item.quantity) for item in session.items],
                key=lambda x: x[0]
            ),
            "scan_ids": sorted([s.id for s in scans]),
            "pickup_ids": sorted([p.id for p in pickups]),
            "sensor_ids": sorted([w.id for w in sensors]),
        }
        raw_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    def evaluate_session(self, session_id: int) -> VerificationResultResponse:
        """
        Executes multi-modal verification for a given shopping session.
        Idempotent: returns existing audit result if evidence fingerprint matches.
        """
        # 1. Fetch Session with Cart Items and Products
        session = (
            self.db.query(ShoppingSession)
            .options(
                joinedload(ShoppingSession.items).joinedload(CartItem.product),
                joinedload(ShoppingSession.verification_events),
            )
            .filter(ShoppingSession.id == session_id)
            .first()
        )

        if not session:
            raise ValueError(f"Shopping session {session_id} not found.")

        # 2. Gather All Multi-Modal Evidence
        scans = self.db.query(ScanEvent).filter(ScanEvent.session_id == session_id).all()
        sensors = self.db.query(SensorEvent).filter(SensorEvent.session_id == session_id).all()

        # Pickup events occurring within session duration (with correlation window tolerance tau)
        session_start = (session.created_at or datetime.now(timezone.utc)) - timedelta(seconds=self.correlation_window)
        session_end = (session.completed_at or session.created_at or datetime.now(timezone.utc)) + timedelta(minutes=5)
        pickups = self.db.query(ShelfPickupEvent).filter(
            ShelfPickupEvent.timestamp >= session_start,
            ShelfPickupEvent.timestamp <= session_end
        ).all()

        # 3. Check Idempotency via Fingerprint
        evidence_hash = self._compute_session_evidence_fingerprint(session, scans, pickups, sensors)
        existing_event = (
            self.db.query(VerificationEvent)
            .filter(VerificationEvent.session_id == session_id)
            .order_by(VerificationEvent.id.desc())
            .first()
        )

        if existing_event and existing_event.evidence_summary.get("evidence_fingerprint") == evidence_hash:
            logger.info(f"Returning cached idempotent verification result for session {session_id} (verification_id={existing_event.verification_id})")
            return self._build_response_from_model(existing_event, session)

        # 4. Execute Correlation Engine
        (
            outcome,
            verdict,
            confidence_score,
            reasons,
            rule_evaluations,
            event_references,
            is_simulated
        ) = self._run_rules(session, scans, pickups, sensors)

        # 5. Separate Checkout Decision
        checkout_decision, staff_review, safety_notice = CheckoutDecisionService.determine_decision(
            outcome=outcome,
            confidence_score=confidence_score,
            is_simulated=is_simulated
        )

        # 6. Build Audit Trail Dictionary
        verification_uuid = str(uuid.uuid4())
        evaluated_at = datetime.now(timezone.utc)
        audit_trail = {
            "evidence_fingerprint": evidence_hash,
            "correlation_window_tau_seconds": self.correlation_window,
            "weight_tolerance_grams": self.weight_tolerance,
            "total_scans": len(scans),
            "total_pickups": len(pickups),
            "total_sensor_events": len(sensors),
            "total_cart_items": len(session.items),
            "reasons": reasons,
            "evaluated_at_iso": evaluated_at.isoformat(),
        }

        # 7. Persist Verification Record and Update Session Status
        verif_model = VerificationEvent(
            verification_id=verification_uuid,
            session_id=session.id,
            outcome=outcome.value,
            verdict=verdict,
            confidence_score=confidence_score,
            checkout_decision=checkout_decision.value,
            staff_review_recommended=staff_review,
            is_simulated=is_simulated,
            evidence_summary={
                "audit_trail": audit_trail,
                "reasons": reasons,
                "rule_evaluations": [r.model_dump() for r in rule_evaluations],
                "event_references": [e.model_dump(mode="json") for e in event_references],
                "safety_notice": safety_notice,
                "evidence_fingerprint": evidence_hash,
            }
        )
        self.db.add(verif_model)

        # Update session status based on decision
        if checkout_decision == CheckoutDecision.AUTO_APPROVE:
            session.status = "COMPLETED"
            session.completed_at = evaluated_at
        elif staff_review:
            session.status = "FLAGGED" if outcome == VerificationOutcome.POTENTIAL_DISCREPANCY else "VERIFYING"

        self.db.commit()
        self.db.refresh(verif_model)

        logger.info(
            f"Session {session_id} verified: outcome={outcome.value}, decision={checkout_decision.value}, "
            f"confidence={confidence_score:.2f}, simulated={is_simulated}"
        )

        return VerificationResultResponse(
            verification_id=verification_uuid,
            session_id=session.id,
            outcome=outcome,
            verdict=verdict,
            checkout_decision=checkout_decision,
            confidence_score=confidence_score,
            staff_review_recommended=staff_review,
            is_simulated=is_simulated,
            reasons=reasons,
            safety_and_trust_notice=safety_notice,
            relevant_event_references=event_references,
            rule_evaluations=rule_evaluations,
            session_items_count=sum(i.quantity for i in session.items),
            scans_count=len(scans),
            pickups_count=len(pickups),
            sensor_events_count=len(sensors),
            evaluated_at=evaluated_at,
            audit_trail=audit_trail,
        )

    def _run_rules(
        self,
        session: ShoppingSession,
        scans: List[ScanEvent],
        pickups: List[ShelfPickupEvent],
        sensors: List[SensorEvent]
    ) -> Tuple[VerificationOutcome, str, float, List[str], List[RuleEvaluationDetail], List[EventReferenceItem], bool]:
        """
        Internal rule engine evaluating evidence, tracking simulated flags,
        and cleanly distinguishing missing evidence from contradictory evidence.
        """
        reasons: List[str] = []
        rule_evaluations: List[RuleEvaluationDetail] = []
        event_references: List[EventReferenceItem] = []

        is_simulated = any(
            [s.is_simulated for s in scans] +
            [p.is_simulated for p in pickups] +
            [w.is_simulated for w in sensors]
        )

        has_contradiction = False
        has_time_drift = False
        has_missing_sensor_modality = False
        corroborated_item_count = 0

        # Build Event References for Transparency
        for s in scans:
            p_name = s.product.name if s.product else f"Product #{s.product_id}"
            event_references.append(
                EventReferenceItem(
                    event_type="SCAN",
                    event_id=s.id,
                    product_id=s.product_id,
                    product_name=p_name,
                    timestamp=s.client_timestamp or s.created_at,
                    confidence=1.0,
                    is_simulated=s.is_simulated,
                    summary=f"Barcode scan of {p_name} (Qty: {s.quantity})"
                )
            )

        for p in pickups:
            p_name = p.product.name if p.product else f"Class '{p.detected_class}'"
            event_references.append(
                EventReferenceItem(
                    event_type="PICKUP",
                    event_id=p.id,
                    product_id=p.product_id,
                    product_name=p_name,
                    timestamp=p.timestamp,
                    confidence=p.confidence,
                    is_simulated=p.is_simulated,
                    summary=f"Camera observed {p.quantity_removed}x {p_name} on Shelf {p.shelf_id}"
                )
            )

        for w in sensors:
            event_references.append(
                EventReferenceItem(
                    event_type="SENSOR",
                    event_id=w.id,
                    timestamp=w.timestamp,
                    confidence=0.95,
                    is_simulated=w.is_simulated,
                    summary=f"Weight delta {w.delta_weight_g:+.1f}g ({w.sensor_type})"
                )
            )

        # ---------------------------------------------------------------------
        # Rule 1: Cart Items vs Barcode Scans Consistency
        # ---------------------------------------------------------------------
        cart_total_qty = sum(item.quantity for item in session.items)
        scans_total_qty = sum(scan.quantity for scan in scans)

        if cart_total_qty == scans_total_qty:
            rule_evaluations.append(
                RuleEvaluationDetail(
                    rule_name="RULE_CART_SCAN_CONSISTENCY",
                    status="PASSED",
                    explanation=f"Cart item count ({cart_total_qty}) matches registered barcode scan events ({scans_total_qty}).",
                    confidence_impact=+0.25,
                    evidence_ids=[s.id for s in scans]
                )
            )
        else:
            has_contradiction = True
            reasons.append(
                f"Cart quantity discrepancy: virtual cart has {cart_total_qty} items, but {scans_total_qty} scans recorded."
            )
            rule_evaluations.append(
                RuleEvaluationDetail(
                    rule_name="RULE_CART_SCAN_CONSISTENCY",
                    status="FAILED",
                    explanation=f"Cart items ({cart_total_qty}) do not equal scanned events ({scans_total_qty}).",
                    confidence_impact=-0.50,
                    evidence_ids=[s.id for s in scans]
                )
            )

        # ---------------------------------------------------------------------
        # Rule 2: Vision Pickup vs Scans Correlation
        # ---------------------------------------------------------------------
        # Check for Unscanned Pickups (camera saw an item removed, but 0 matching scans)
        for pickup in pickups:
            # Try to match with a scan event
            matching_scan: Optional[ScanEvent] = None
            for scan in scans:
                # Match by product ID or category ILIKE detected_class
                is_prod_match = (
                    (pickup.product_id and scan.product_id == pickup.product_id) or
                    (scan.product and scan.product.category.lower() in pickup.detected_class.lower()) or
                    (scan.product and pickup.detected_class.lower() in scan.product.category.lower())
                )
                if is_prod_match:
                    matching_scan = scan
                    break

            if not matching_scan:
                # Direct Contradiction: Shelf observation without any matching scan
                has_contradiction = True
                item_label = pickup.product.name if pickup.product else f"'{pickup.detected_class}'"
                if len(scans) > 0:
                    scanned_names = ", ".join([s.product.name if s.product else f"#{s.product_id}" for s in scans])
                    reasons.append(
                        f"Product mismatch / class conflict: camera observed removal of {item_label} from Shelf #{pickup.shelf_id}, "
                        f"but shopper registered scan for [{scanned_names}]."
                    )
                else:
                    reasons.append(
                        f"Unscanned item pickup detected: camera observed {pickup.quantity_removed}x {item_label} "
                        f"removed from Shelf #{pickup.shelf_id}, but no corresponding scan occurred."
                    )
                rule_evaluations.append(
                    RuleEvaluationDetail(
                        rule_name="RULE_VISION_PICKUP_CORRELATION",
                        status="FAILED",
                        explanation=f"Camera observed {item_label} removed from Shelf {pickup.shelf_id} with conflicting or missing scan.",
                        confidence_impact=-0.40,
                        evidence_ids=[pickup.id]
                    )
                )
            else:
                # Matching scan found; check quantity consistency
                if pickup.quantity_removed != matching_scan.quantity:
                    has_contradiction = True
                    reasons.append(
                        f"Quantity mismatch for {matching_scan.product.name if matching_scan.product else 'item'}: "
                        f"camera observed {pickup.quantity_removed} units removed, but shopper scanned {matching_scan.quantity}."
                    )
                    rule_evaluations.append(
                        RuleEvaluationDetail(
                            rule_name="RULE_VISION_PICKUP_CORRELATION",
                            status="FAILED",
                            explanation=f"Observed quantity {pickup.quantity_removed} != scanned quantity {matching_scan.quantity}.",
                            confidence_impact=-0.35,
                            evidence_ids=[pickup.id, matching_scan.id]
                        )
                    )
                else:
                    # Check temporal synchronization window
                    t_scan = matching_scan.client_timestamp or matching_scan.created_at
                    t_pickup = pickup.timestamp
                    delta_seconds = abs((t_pickup - t_scan).total_seconds())

                    if delta_seconds > self.correlation_window:
                        has_time_drift = True
                        reasons.append(
                            f"Temporal synchronization drift: camera pickup and barcode scan occurred "
                            f"{delta_seconds:.1f}s apart (threshold tau={self.correlation_window:.1f}s)."
                        )
                        rule_evaluations.append(
                            RuleEvaluationDetail(
                                rule_name="RULE_TEMPORAL_SYNCHRONIZATION",
                                status="INCONCLUSIVE",
                                explanation=f"Event time drift dt={delta_seconds:.1f}s exceeded correlation window tau={self.correlation_window}s.",
                                confidence_impact=-0.20,
                                evidence_ids=[pickup.id, matching_scan.id]
                            )
                        )
                    else:
                        corroborated_item_count += 1
                        rule_evaluations.append(
                            RuleEvaluationDetail(
                                rule_name="RULE_VISION_PICKUP_CORRELATION",
                                status="PASSED",
                                explanation=(
                                    f"Camera pickup corroborated barcode scan within {delta_seconds:.1f}s "
                                    f"(confidence: {pickup.confidence * 100:.0f}%)."
                                ),
                                confidence_impact=+0.35,
                                evidence_ids=[pickup.id, matching_scan.id]
                            )
                        )

        # Check for Barcode Scans with NO Vision Pickups (Shelf missing camera or occluded)
        if len(scans) > 0 and len(pickups) == 0:
            has_missing_sensor_modality = True
            reasons.append(
                "Camera telemetry absent: no vision pickup events recorded for scanned items. "
                "Shelf may be unequipped with overhead optics or occluded; not treated as contradiction."
            )
            rule_evaluations.append(
                RuleEvaluationDetail(
                    rule_name="RULE_VISION_PICKUP_CORRELATION",
                    status="SKIPPED",
                    explanation="Camera pickup telemetry unavailable for this session. Modality missing.",
                    confidence_impact=-0.10,
                    evidence_ids=[s.id for s in scans]
                )
            )

        # ---------------------------------------------------------------------
        # Rule 3: Weight Sensor Telemetry Correlation
        # ---------------------------------------------------------------------
        shelf_scales = [w for w in sensors if w.sensor_type == "WEIGHT_SHELF"]
        cart_scales = [w for w in sensors if w.sensor_type == "WEIGHT_CART"]

        if len(shelf_scales) == 0 and len(cart_scales) == 0:
            has_missing_sensor_modality = True
            reasons.append(
                "Load-cell telemetry absent: no weight telemetry recorded from shelf or cart scales. "
                "Hardware sensor absent; not treated as contradiction."
            )
            rule_evaluations.append(
                RuleEvaluationDetail(
                    rule_name="RULE_WEIGHT_TELEMETRY_CORRELATION",
                    status="SKIPPED",
                    explanation="Weight scales not available or did not trigger for this session.",
                    confidence_impact=-0.10,
                    evidence_ids=[]
                )
            )
        else:
            # Check weight correlation for scanned products
            for scan in scans:
                product = scan.product
                if not product:
                    continue

                expected_weight_g = product.tare_weight_g * scan.quantity
                # Match cart weight delta
                for cart_scale in cart_scales:
                    diff = abs(cart_scale.delta_weight_g - expected_weight_g)
                    if diff <= self.weight_tolerance:
                        rule_evaluations.append(
                            RuleEvaluationDetail(
                                rule_name="RULE_WEIGHT_TELEMETRY_CORRELATION",
                                status="PASSED",
                                explanation=f"Cart scale (+{cart_scale.delta_weight_g:.1f}g) matches {product.name} weight ({expected_weight_g:.1f}g ± {self.weight_tolerance}g).",
                                confidence_impact=+0.25,
                                evidence_ids=[cart_scale.id, scan.id]
                            )
                        )
                    else:
                        has_contradiction = True
                        reasons.append(
                            f"Weight discrepancy on cart scale: measured {cart_scale.delta_weight_g:+.1f}g, "
                            f"expected {expected_weight_g:.1f}g for {product.name} (exceeds {self.weight_tolerance}g tolerance)."
                        )
                        rule_evaluations.append(
                            RuleEvaluationDetail(
                                rule_name="RULE_WEIGHT_TELEMETRY_CORRELATION",
                                status="FAILED",
                                explanation=f"Cart scale delta {cart_scale.delta_weight_g:+.1f}g outside tare tolerance {self.weight_tolerance}g.",
                                confidence_impact=-0.35,
                                evidence_ids=[cart_scale.id, scan.id]
                            )
                        )

        # ---------------------------------------------------------------------
        # Final Outcome Formulation
        # ---------------------------------------------------------------------
        if has_contradiction:
            outcome = VerificationOutcome.POTENTIAL_DISCREPANCY
            verdict = "MISMATCH"
            confidence_score = 0.35
        elif has_time_drift:
            outcome = VerificationOutcome.INCONCLUSIVE
            verdict = "UNCERTAIN"
            confidence_score = 0.60
        elif has_missing_sensor_modality and len(scans) > 0 and (len(pickups) == 0 and len(sensors) == 0):
            # Only single modality (barcode scan) with NO corroborating physical telemetry
            outcome = VerificationOutcome.INCONCLUSIVE
            verdict = "UNCERTAIN"
            confidence_score = 0.70
            reasons.append("Single modality only: Barcode scanned without corroborating camera or weight sensors.")
        elif len(session.items) == 0 and len(scans) == 0 and len(pickups) == 0:
            outcome = VerificationOutcome.NO_DISCREPANCY_DETECTED
            verdict = "CONSISTENT"
            confidence_score = 1.0
            reasons.append("Empty shopping session with no items or physical events.")
        else:
            outcome = VerificationOutcome.NO_DISCREPANCY_DETECTED
            verdict = "CONSISTENT"
            confidence_score = 0.95
            reasons.append("Multi-modal sensor telemetry and barcode scans are consistent within configured thresholds.")

        return outcome, verdict, confidence_score, reasons, rule_evaluations, event_references, is_simulated

    def _build_response_from_model(self, model: VerificationEvent, session: ShoppingSession) -> VerificationResultResponse:
        """Constructs response from persisted VerificationEvent ORM instance."""
        summary = model.evidence_summary or {}
        audit = summary.get("audit_trail", {})
        reasons = summary.get("reasons", [model.verdict])
        safety_notice = summary.get("safety_notice", CheckoutDecisionService.SAFETY_NOTICE)
        rule_evals = [RuleEvaluationDetail(**r) for r in summary.get("rule_evaluations", [])]
        event_refs = [EventReferenceItem(**e) for e in summary.get("event_references", [])]

        outcome_val = model.outcome or (
            VerificationOutcome.NO_DISCREPANCY_DETECTED.value if model.verdict == "CONSISTENT"
            else VerificationOutcome.POTENTIAL_DISCREPANCY.value if model.verdict == "MISMATCH"
            else VerificationOutcome.INCONCLUSIVE.value
        )
        decision_val = model.checkout_decision or (
            CheckoutDecision.AUTO_APPROVE.value if model.verdict == "CONSISTENT"
            else CheckoutDecision.STAFF_REVIEW_RECOMMENDED.value
        )

        return VerificationResultResponse(
            verification_id=model.verification_id or f"verif-{model.id}",
            session_id=model.session_id,
            outcome=VerificationOutcome(outcome_val),
            verdict=model.verdict,
            checkout_decision=CheckoutDecision(decision_val),
            confidence_score=model.confidence_score,
            staff_review_recommended=model.staff_review_recommended,
            is_simulated=model.is_simulated,
            reasons=reasons,
            safety_and_trust_notice=safety_notice,
            relevant_event_references=event_refs,
            rule_evaluations=rule_evals,
            session_items_count=sum(i.quantity for i in session.items),
            scans_count=len(session.scans),
            pickups_count=audit.get("total_pickups", 0),
            sensor_events_count=audit.get("total_sensor_events", 0),
            evaluated_at=model.created_at,
            audit_trail=audit,
        )
