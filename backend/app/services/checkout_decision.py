"""
SmartCart AI - Checkout Decision Manager
Separates high-level retail checkout decisions from low-level evidence-correlation logic.
Ensures trustworthy, customer-centric operations where discrepancies trigger staff review
rather than automated accusations or harsh penalties.
"""

from typing import Dict, Any, Tuple
from backend.app.schemas.verification import VerificationOutcome, CheckoutDecision
from backend.app.core.config import settings
from backend.app.core.logging import logger


class CheckoutDecisionService:
    """
    Decoupled service that takes the output of the evidence correlation engine
    and determines the retail checkout disposition.
    """

    SAFETY_NOTICE = (
        "Notice: Multi-modal sensor discrepancies indicate an observation variance or sensor uncertainty, "
        "not deliberate wrongdoing. All flagged sessions are handled respectfully via friendly store attendant assistance."
    )

    SIMULATION_NOTICE = (
        "Notice: Physical verification was evaluated using simulated sensor telemetry. "
        "Simulated events provide functional verification and testing without hardware dependency."
    )

    @classmethod
    def determine_decision(
        cls,
        outcome: VerificationOutcome,
        confidence_score: float,
        is_simulated: bool = False
    ) -> Tuple[CheckoutDecision, bool, str]:
        """
        Calculates checkout decision, staff review recommendation, and customer-facing notice.

        Returns:
            (CheckoutDecision, staff_review_recommended, notice_message)
        """
        if outcome == VerificationOutcome.NO_DISCREPANCY_DETECTED:
            if confidence_score >= settings.MIN_VERIFICATION_CONFIDENCE:
                decision = CheckoutDecision.AUTO_APPROVE
                staff_review = False
                notice = "Session verified successfully. Self-checkout auto-approved."
            else:
                decision = CheckoutDecision.STAFF_REVIEW_RECOMMENDED
                staff_review = True
                notice = (
                    f"No discrepancies detected, but verification confidence ({confidence_score:.2f}) "
                    f"is below auto-approval threshold ({settings.MIN_VERIFICATION_CONFIDENCE:.2f}). "
                    f"Attendant spot check recommended."
                )

        elif outcome == VerificationOutcome.POTENTIAL_DISCREPANCY:
            decision = CheckoutDecision.STAFF_REVIEW_RECOMMENDED
            staff_review = True
            notice = f"Potential variance detected across sensor telemetry. {cls.SAFETY_NOTICE}"

        else:  # INCONCLUSIVE
            if settings.ALLOW_INCONCLUSIVE_CHECKOUT_BYPASS:
                decision = CheckoutDecision.AUTO_APPROVE
                staff_review = False
                notice = "Inconclusive sensor data bypassed by store policy. Proceeding to checkout."
            else:
                decision = CheckoutDecision.STAFF_REVIEW_RECOMMENDED
                staff_review = True
                notice = f"Telemetry data was insufficient or ambiguous for conclusive auto-verification. {cls.SAFETY_NOTICE}"

        if is_simulated:
            notice = f"{notice} [{cls.SIMULATION_NOTICE}]"

        logger.info(f"Checkout decision evaluated: decision={decision.value}, staff_review={staff_review}, outcome={outcome.value}")
        return decision, staff_review, notice
