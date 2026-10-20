"""
SmartCart AI - Verification Engine Test Suite
Tests matching events, unmatched pickups, quantity mismatches, delayed events,
conflicting evidence, insufficient evidence, idempotency, and REST API endpoints.
"""

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.models.shelf import Shelf
from backend.app.models.session import ShoppingSession, CartItem, ScanEvent
from backend.app.models.verification import SensorEvent, ShelfPickupEvent, VerificationEvent
from backend.app.schemas.verification import VerificationOutcome, CheckoutDecision


def _create_active_session(db: Session, user_id="test_user_01", cart_id="cart_test_01") -> ShoppingSession:
    session = ShoppingSession(user_id=user_id, cart_id=cart_id, status="ACTIVE")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_matching_events_scenario(client: TestClient, db_session: Session):
    """
    Scenario 1: Matching events across all modalities.
    Expected: NO_DISCREPANCY_DETECTED, AUTO_APPROVE, confidence >= 0.85.
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    # 1. Vision pickup
    pickup = ShelfPickupEvent(
        shelf_id=1,
        product_id=cereal.id,
        detected_class="cereal",
        confidence=0.94,
        quantity_removed=1,
        timestamp=now,
        is_simulated=True
    )
    db_session.add(pickup)

    # 2. Barcode scan 2s later
    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        client_timestamp=now + timedelta(seconds=2),
        is_simulated=True
    )
    db_session.add(scan)

    # 3. Cart Item
    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)

    # 4. Cart scale delta (+450g)
    scale = SensorEvent(
        sensor_id="SCALE-CART-01",
        sensor_type="WEIGHT_CART",
        delta_weight_g=450.0,
        session_id=session.id,
        timestamp=now + timedelta(seconds=3),
        is_simulated=True
    )
    db_session.add(scale)
    db_session.commit()

    # Call API to verify
    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.NO_DISCREPANCY_DETECTED.value
    assert data["verdict"] == "CONSISTENT"
    assert data["checkout_decision"] == CheckoutDecision.AUTO_APPROVE.value
    assert data["staff_review_recommended"] is False
    assert data["confidence_score"] >= 0.85
    assert data["is_simulated"] is True
    assert "auto-approved" in data["safety_and_trust_notice"].lower()


def test_unmatched_pickup_discrepancy(client: TestClient, db_session: Session):
    """
    Scenario 2: Unmatched Pickup (item removed, no scan event).
    Expected: POTENTIAL_DISCREPANCY, STAFF_REVIEW_RECOMMENDED, polite notice.
    """
    session = _create_active_session(db_session)
    butter = db_session.query(Product).filter(Product.category == "butter").first() or db_session.query(Product).first()
    now = datetime.now(timezone.utc)

    # Camera sees item removed, but customer did NOT scan it
    pickup = ShelfPickupEvent(
        shelf_id=1,
        product_id=butter.id,
        detected_class=butter.category,
        confidence=0.92,
        quantity_removed=1,
        timestamp=now,
        is_simulated=True
    )
    db_session.add(pickup)
    db_session.commit()

    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.POTENTIAL_DISCREPANCY.value
    assert data["verdict"] == "MISMATCH"
    assert data["checkout_decision"] == CheckoutDecision.STAFF_REVIEW_RECOMMENDED.value
    assert data["staff_review_recommended"] is True
    assert any("unscanned item pickup detected" in r.lower() for r in data["reasons"])
    # Trust & Safety: ensure no accusations of theft
    assert "not deliberate wrongdoing" in data["safety_and_trust_notice"].lower()


def test_quantity_mismatch_discrepancy(client: TestClient, db_session: Session):
    """
    Scenario 3: Quantity mismatch (Camera saw 2 items removed, only 1 scanned).
    Expected: POTENTIAL_DISCREPANCY.
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    pickup = ShelfPickupEvent(
        shelf_id=1,
        product_id=cereal.id,
        detected_class="cereal",
        confidence=0.90,
        quantity_removed=2,  # 2 units removed
        timestamp=now,
        is_simulated=True
    )
    db_session.add(pickup)

    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,  # Only 1 scanned
        client_timestamp=now + timedelta(seconds=2),
        is_simulated=True
    )
    db_session.add(scan)

    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)
    db_session.commit()

    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.POTENTIAL_DISCREPANCY.value
    assert data["staff_review_recommended"] is True
    assert any("quantity mismatch" in r.lower() for r in data["reasons"])


def test_delayed_events_time_drift(client: TestClient, db_session: Session):
    """
    Scenario 4: Delayed events arriving outside tau (dt = 45s > 15s).
    Expected: INCONCLUSIVE, STAFF_REVIEW_RECOMMENDED (not an accusation).
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    # Scan at t
    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        client_timestamp=now,
        is_simulated=True
    )
    db_session.add(scan)

    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)

    # Pickup arrives 45s later (drift outside tau=15s)
    pickup = ShelfPickupEvent(
        shelf_id=1,
        product_id=cereal.id,
        detected_class="cereal",
        confidence=0.90,
        quantity_removed=1,
        timestamp=now + timedelta(seconds=45),
        is_simulated=True
    )
    db_session.add(pickup)
    db_session.commit()

    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.INCONCLUSIVE.value
    assert data["verdict"] == "UNCERTAIN"
    assert data["staff_review_recommended"] is True
    assert any("temporal synchronization drift" in r.lower() for r in data["reasons"])


def test_insufficient_evidence_missing_sensors(client: TestClient, db_session: Session):
    """
    Scenario 5: Insufficient evidence (Barcode scan recorded, but no camera or weight scale available).
    Expected: INCONCLUSIVE (single modality only, absence of sensor is NOT an accusation of theft).
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        client_timestamp=now,
        is_simulated=False
    )
    db_session.add(scan)

    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)
    db_session.commit()

    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.INCONCLUSIVE.value
    assert data["verdict"] == "UNCERTAIN"
    assert data["staff_review_recommended"] is True
    assert any("camera telemetry absent" in r.lower() for r in data["reasons"])
    assert any("load-cell telemetry absent" in r.lower() for r in data["reasons"])


def test_conflicting_weight_evidence(client: TestClient, db_session: Session):
    """
    Scenario 6: Conflicting weight telemetry (e.g. cart scale delta deviates from tare weight by > 50g).
    Expected: POTENTIAL_DISCREPANCY.
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        client_timestamp=now,
        is_simulated=True
    )
    db_session.add(scan)

    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)

    pickup = ShelfPickupEvent(
        shelf_id=1,
        product_id=cereal.id,
        detected_class="cereal",
        confidence=0.91,
        quantity_removed=1,
        timestamp=now + timedelta(seconds=1),
        is_simulated=True
    )
    db_session.add(pickup)

    # Cart scale reports +950g instead of 450g (+500g error)
    scale = SensorEvent(
        sensor_id="SCALE-CART-01",
        sensor_type="WEIGHT_CART",
        delta_weight_g=950.0,
        session_id=session.id,
        timestamp=now + timedelta(seconds=2),
        is_simulated=True
    )
    db_session.add(scale)
    db_session.commit()

    response = client.post(f"/api/v1/verification/verify/{session.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == VerificationOutcome.POTENTIAL_DISCREPANCY.value
    assert data["staff_review_recommended"] is True
    assert any("weight discrepancy on cart scale" in r.lower() for r in data["reasons"])


def test_verification_idempotency(client: TestClient, db_session: Session):
    """
    Scenario 7: Repeated verify requests on an unchanged session return
    the same consistent result without creating inconsistent duplicates.
    """
    session = _create_active_session(db_session)
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    now = datetime.now(timezone.utc)

    scan = ScanEvent(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        client_timestamp=now,
        is_simulated=True
    )
    db_session.add(scan)
    cart_item = CartItem(
        session_id=session.id,
        product_id=cereal.id,
        quantity=1,
        unit_price=cereal.price
    )
    db_session.add(cart_item)
    db_session.commit()

    # First verification
    resp1 = client.post(f"/api/v1/verification/verify/{session.id}")
    assert resp1.status_code == 200
    data1 = resp1.json()
    verif_id_1 = data1["verification_id"]

    # Second verification with no evidence changes
    resp2 = client.post(f"/api/v1/verification/verify/{session.id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    verif_id_2 = data2["verification_id"]

    assert verif_id_1 == verif_id_2
    assert data1["outcome"] == data2["outcome"]
    assert data1["confidence_score"] == data2["confidence_score"]

    # Verify query by ID endpoint works
    resp3 = client.get(f"/api/v1/verification/{verif_id_1}")
    assert resp3.status_code == 200
    assert resp3.json()["verification_id"] == verif_id_1

    # Verify query by session ID endpoint works
    resp4 = client.get(f"/api/v1/verification/session/{session.id}")
    assert resp4.status_code == 200
    assert resp4.json()["verification_id"] == verif_id_1


def test_verification_rules_endpoint(client: TestClient):
    """
    Test retrieving active configurable verification rules.
    """
    response = client.get("/api/v1/verification/rules")
    assert response.status_code == 200
    data = response.json()

    assert "correlation_window_seconds" in data
    assert "weight_tolerance_grams" in data
    assert "min_verification_confidence" in data
    assert len(data["configured_rules"]) >= 4
