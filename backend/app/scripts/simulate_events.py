"""
SmartCart AI - Deterministic Multi-Modal Telemetry & Sensor Simulator
Simulates retail edge telemetry (scans, camera pickups, load-cells) across 6 test scenarios.
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from backend.app.core.database import SessionLocal, engine
from backend.app.core.logging import logger
from backend.app.models import Base
from backend.app.models.product import Product
from backend.app.models.shelf import Shelf
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.models.verification import SensorEvent, ShelfPickupEvent


def get_or_create_demo_session(db, user_id="sim_shopper_01", cart_id="sim_cart_01") -> ShoppingSession:
    session = ShoppingSession(
        user_id=user_id,
        cart_id=cart_id,
        status="ACTIVE"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"[SIMULATOR] Created active session ID={session.id} for user={user_id}")
    return session


def run_scenario(scenario_name: str, time_offset_minutes: int = 0) -> Dict[str, Any]:
    """
    Execute a deterministic simulation scenario and persist events labeled with is_simulated=True.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc) + timedelta(minutes=time_offset_minutes * 10)
        session = get_or_create_demo_session(db)
        session.created_at = now
        db.commit()

        if scenario_name == "normal_purchase":
            # Scenario 1: Matching Scan, Camera Pickup, and Weight Shift
            cereal = db.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
            shelf_a1 = db.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()

            # 1. Vision Pickup at t
            pickup = ShelfPickupEvent(
                shelf_id=shelf_a1.id if shelf_a1 else 1,
                product_id=cereal.id if cereal else 1,
                detected_class="cereal",
                confidence=0.94,
                quantity_removed=1,
                timestamp=now,
                is_simulated=True,
                raw_metadata={"note": "Simulated front facing removal"}
            )
            db.add(pickup)

            # 2. Shelf Scale Delta at t + 1s (-450g)
            scale_shelf = SensorEvent(
                sensor_id="SCALE-SHELF-BAY-A1",
                sensor_type="WEIGHT_SHELF",
                delta_weight_g=-450.0,
                shelf_id=shelf_a1.id if shelf_a1 else 1,
                timestamp=now + timedelta(seconds=1),
                is_simulated=True
            )
            db.add(scale_shelf)

            # 3. Barcode Scan at t + 3s
            scan = ScanEvent(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                client_timestamp=now + timedelta(seconds=3),
                idempotency_key=f"sim-scan-{int(time.time())}",
                is_simulated=True,
                raw_payload={"barcode": cereal.barcode if cereal else "8901030018241"}
            )
            db.add(scan)

            # 4. Cart Item Update
            cart_item = CartItem(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                unit_price=cereal.price if cereal else 4.99
            )
            db.add(cart_item)

            # 5. Cart Scale Delta at t + 5s (+450g)
            scale_cart = SensorEvent(
                sensor_id=f"SCALE-CART-{session.cart_id}",
                sensor_type="WEIGHT_CART",
                delta_weight_g=450.0,
                session_id=session.id,
                timestamp=now + timedelta(seconds=5),
                is_simulated=True
            )
            db.add(scale_cart)

            db.commit()
            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "CONSISTENT",
                "evidence_count": 4,
                "description": "Camera observed cereal pickup, shelf scale delta -450g, barcode scanned within 3s, cart scale +450g."
            }

        elif scenario_name == "unscanned_pickup":
            # Scenario 2: Unmatched Pickup (Theft or Loss Prevention Trigger)
            butter = db.query(Product).filter(Product.sku == "BUTTER-AMUL-01").first()
            shelf_b = db.query(Shelf).filter(Shelf.bay_code == "BAY-B4").first()

            # 1. Vision Pickup at t
            pickup = ShelfPickupEvent(
                shelf_id=shelf_b.id if shelf_b else 2,
                product_id=butter.id if butter else 10,
                detected_class="dairy_butter",
                confidence=0.91,
                quantity_removed=1,
                timestamp=now,
                is_simulated=True
            )
            db.add(pickup)

            # 2. Shelf Scale Delta at t + 1s (-510g)
            scale_shelf = SensorEvent(
                sensor_id="SCALE-SHELF-BAY-B4",
                sensor_type="WEIGHT_SHELF",
                delta_weight_g=-510.0,
                shelf_id=shelf_b.id if shelf_b else 2,
                timestamp=now + timedelta(seconds=1),
                is_simulated=True
            )
            db.add(scale_shelf)
            # NO matching scan is added!

            db.commit()
            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "MISMATCH (UNSCANNED_PICKUP)",
                "evidence_count": 2,
                "description": "Camera and scale detected butter removal, but NO scan event occurred within timeout window."
            }

        elif scenario_name == "product_mismatch":
            # Scenario 3: Product Mismatch (Barcode Swap)
            tea = db.query(Product).filter(Product.sku == "TEA-LIPTON-01").first()
            noodles = db.query(Product).filter(Product.sku == "NOODLES-MAGGI-01").first()
            shelf_b = db.query(Shelf).filter(Shelf.bay_code == "BAY-B3").first()

            # Camera sees Tea removed (250g)
            pickup = ShelfPickupEvent(
                shelf_id=shelf_b.id if shelf_b else 2,
                product_id=tea.id if tea else 6,
                detected_class="tea",
                confidence=0.88,
                quantity_removed=1,
                timestamp=now,
                is_simulated=True
            )
            db.add(pickup)

            # User scans Noodles (0.99, 140g)
            scan = ScanEvent(
                session_id=session.id,
                product_id=noodles.id if noodles else 12,
                quantity=1,
                client_timestamp=now + timedelta(seconds=2),
                idempotency_key=f"sim-mismatch-{int(time.time())}",
                is_simulated=True,
                raw_payload={"barcode": noodles.barcode if noodles else "8901030122211"}
            )
            db.add(scan)
            db.add(CartItem(
                session_id=session.id,
                product_id=noodles.id if noodles else 12,
                quantity=1,
                unit_price=noodles.price if noodles else 0.99
            ))

            db.commit()
            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "MISMATCH (CLASS_CONFLICT)",
                "evidence_count": 2,
                "description": "Camera observed 'tea' removal, but shopper scanned 'instant_noodles'."
            }

        elif scenario_name == "quantity_mismatch":
            # Scenario 4: Quantity Mismatch (2 items picked up, 1 scanned)
            soup = db.query(Product).filter(Product.sku == "SOUP-CAMPBELL-01").first()
            shelf_c = db.query(Shelf).filter(Shelf.bay_code == "BAY-C3").first()

            pickup = ShelfPickupEvent(
                shelf_id=shelf_c.id if shelf_c else 3,
                product_id=soup.id if soup else 9,
                detected_class="soup",
                confidence=0.92,
                quantity_removed=2,  # 2 cans observed
                timestamp=now,
                is_simulated=True
            )
            db.add(pickup)

            # User scans only 1 can
            scan = ScanEvent(
                session_id=session.id,
                product_id=soup.id if soup else 9,
                quantity=1,
                client_timestamp=now + timedelta(seconds=2),
                is_simulated=True
            )
            db.add(scan)
            db.add(CartItem(
                session_id=session.id,
                product_id=soup.id if soup else 9,
                quantity=1,
                unit_price=soup.price if soup else 2.50
            ))

            db.commit()
            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "MISMATCH (QUANTITY_CONFLICT)",
                "evidence_count": 2,
                "description": "Camera observed 2 cans removed, but only 1 can was scanned."
            }

        elif scenario_name == "delayed_evidence":
            # Scenario 5: Delayed Evidence (Arrived after tau = 15s)
            cereal = db.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

            # User scanned at t
            scan = ScanEvent(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                client_timestamp=now,
                is_simulated=True
            )
            db.add(scan)
            db.add(CartItem(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                unit_price=cereal.price if cereal else 4.99
            ))

            # Camera event arrives at t + 45s (out of synchronization window)
            pickup = ShelfPickupEvent(
                shelf_id=1,
                product_id=cereal.id if cereal else 1,
                detected_class="cereal",
                confidence=0.90,
                quantity_removed=1,
                timestamp=now + timedelta(seconds=45),
                is_simulated=True
            )
            db.add(pickup)

            db.commit()
            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "UNCERTAIN (TIME_DRIFT)",
                "evidence_count": 2,
                "description": "Evidence arrived with dt=45s (> tau=15s), triggering uncertain review."
            }

        elif scenario_name == "missing_evidence":
            # Scenario 6: Missing Evidence (Sensor failure or camera blocked)
            cereal = db.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
            scan = ScanEvent(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                client_timestamp=now,
                is_simulated=True
            )
            db.add(scan)
            db.add(CartItem(
                session_id=session.id,
                product_id=cereal.id if cereal else 1,
                quantity=1,
                unit_price=cereal.price if cereal else 4.99
            ))
            db.commit()

            return {
                "scenario": scenario_name,
                "status": "SUCCESS",
                "session_id": session.id,
                "expected_verdict": "UNCERTAIN (NO_CORROBORATING_TELEMETRY)",
                "evidence_count": 1,
                "description": "Shopper scanned product, but no visual or scale telemetry corroborated."
            }

        else:
            raise ValueError(f"Unknown scenario: {scenario_name}")

    finally:
        db.close()


ALL_SCENARIOS = [
    "normal_purchase",
    "unscanned_pickup",
    "product_mismatch",
    "quantity_mismatch",
    "delayed_evidence",
    "missing_evidence"
]


def main():
    from backend.app.services.verification_engine import VerificationEngine

    parser = argparse.ArgumentParser(description="SmartCart AI Multi-Modal Telemetry Simulator")
    parser.add_argument(
        "--scenario",
        choices=ALL_SCENARIOS + ["all"],
        default="normal_purchase",
        help="Test scenario to generate (or 'all' to run full suite)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Automatically run verification engine after simulating scenario"
    )
    args = parser.parse_args()

    scenarios_to_run = ALL_SCENARIOS if args.scenario == "all" else [args.scenario]

    db = SessionLocal()
    engine = VerificationEngine(db)

    try:
        for i, sc in enumerate(scenarios_to_run):
            print(f"\n=======================================================")
            print(f"=== Simulation Scenario: {sc} ===")
            print(f"=======================================================")
            result = run_scenario(sc, time_offset_minutes=i)
            print(f"Scenario Status:   {result['status']}")
            print(f"Session ID:        {result['session_id']}")
            print(f"Expected Verdict:  {result['expected_verdict']}")
            print(f"Evidence Created:  {result['evidence_count']} events (is_simulated=True)")
            print(f"Description:       {result['description']}")

            if args.verify:
                verif = engine.evaluate_session(result['session_id'])
                print(f"\n>>> [VERIFICATION ENGINE EVALUATION] <<<")
                print(f"Verification UUID: {verif.verification_id}")
                print(f"Outcome:           {verif.outcome.value}")
                print(f"Legacy Verdict:    {verif.verdict}")
                print(f"Checkout Decision: {verif.checkout_decision.value}")
                print(f"Confidence Score:  {verif.confidence_score * 100:.1f}%")
                print(f"Staff Review:      {verif.staff_review_recommended}")
                print(f"Reasons:           {verif.reasons}")
                print(f"Safety Notice:     {verif.safety_and_trust_notice}")

        if args.scenario == "all":
            print(f"\n[OK] Successfully executed, persisted, and verified all {len(ALL_SCENARIOS)} simulation scenarios.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
