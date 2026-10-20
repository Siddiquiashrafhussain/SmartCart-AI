"""
SmartCart AI - End-to-End Checkout, Verification Decisions & Receipts Test Suite
Tests complete shopping lifecycle: scanning -> evidence correlation -> policy decision ->
idempotent receipt issuance, inventory decrements, and attendant override handling.
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.product import Product, Inventory
from backend.app.models.session import ShoppingSession, CartItem
from backend.app.models.alert import Receipt


def test_checkout_empty_cart_fails(client: TestClient):
    """
    Validation check: Checkout on an empty cart must be rejected.
    """
    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_01", "cart_id": "cart_01"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res.status_code == 400
    assert "empty cart" in res.json()["detail"].lower()


def test_checkout_successful_auto_approve(client: TestClient, db_session: Session):
    """
    Scenario 1: Customer scans product, matching pickup and scale telemetry present.
    Expected: Verification AUTO_APPROVE, session COMPLETED, receipt issued, inventory decremented.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    inv = db_session.query(Inventory).filter(Inventory.product_id == cereal.id).first()
    initial_stock = inv.total_store_stock
    initial_visible = inv.estimated_visible_stock

    # 1. Start Session
    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_alice", "cart_id": "cart_101"})
    session_id = sess_res.json()["id"]

    # 2. Barcode Scan
    scan_res = client.post("/api/v1/events/scan", json={
        "session_id": session_id,
        "barcode": cereal.barcode,
        "quantity": 1
    })
    assert scan_res.status_code in [200, 201]

    # 3. Correlated Pickup & Scale Events
    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 1,
        "confidence": 0.95,
        "timestamp": now.isoformat()
    })
    client.post("/api/v1/events/sensor", json={
        "sensor_id": "SCALE-CART-101",
        "sensor_type": "WEIGHT_CART",
        "delta_weight_g": cereal.tare_weight_g,
        "session_id": session_id,
        "timestamp": now.isoformat()
    })

    # 4. Finalize Checkout
    chk_res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert chk_res.status_code == 200
    data = chk_res.json()

    assert data["session_id"] == session_id
    assert data["session_status"] == "COMPLETED"
    assert data["checkout_finalized"] is True
    assert data["review_required"] is False
    assert data["decision"] == "AUTO_APPROVE"
    assert data["receipt"] is not None
    assert data["receipt"]["total_amount"] == cereal.price
    assert data["receipt"]["item_count"] == 1
    assert data["receipt"]["payment_status"] == "SIMULATED_PAID"
    assert len(data["receipt"]["transaction_hash"]) == 64

    # Verify inventory was decremented in database
    db_session.refresh(inv)
    assert inv.total_store_stock == initial_stock - 1
    assert inv.estimated_visible_stock == initial_visible - 1


def test_checkout_idempotency_repeated_request(client: TestClient, db_session: Session):
    """
    Scenario 2: Client re-sends checkout finalize on already COMPLETED session.
    Expected: Same receipt returned, is_idempotent_replay=True, inventory NOT decremented again.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    inv = db_session.query(Inventory).filter(Inventory.product_id == cereal.id).first()

    # Create session, scan, add matching sensor telemetry
    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_idempotent", "cart_id": "cart_102"})
    session_id = sess_res.json()["id"]

    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": cereal.barcode, "quantity": 1})

    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 1,
        "confidence": 0.95,
        "timestamp": now.isoformat()
    })
    client.post("/api/v1/events/sensor", json={
        "sensor_id": "SCALE-CART-102",
        "sensor_type": "WEIGHT_CART",
        "delta_weight_g": cereal.tare_weight_g,
        "session_id": session_id,
        "timestamp": now.isoformat()
    })

    # First checkout
    res1 = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res1.status_code == 200
    assert res1.json()["checkout_finalized"] is True
    receipt1 = res1.json()["receipt"]
    stock_after_first = inv.total_store_stock

    # Second repeated checkout request
    res2 = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["is_idempotent_replay"] is True
    assert data2["session_status"] == "COMPLETED"
    assert data2["receipt"]["id"] == receipt1["id"]
    assert data2["receipt"]["transaction_hash"] == receipt1["transaction_hash"]

    # Verify stock was not decremented twice
    db_session.refresh(inv)
    assert inv.total_store_stock == stock_after_first


def test_checkout_discrepancy_blocks_and_flags_session(client: TestClient, db_session: Session):
    """
    Scenario 3: Quantity or product mismatch detected during checkout.
    Expected: STAFF_REVIEW_RECOMMENDED, session transitioned to FLAGGED, no receipt issued.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_discrepant", "cart_id": "cart_103"})
    session_id = sess_res.json()["id"]

    # Customer scanned 1 cereal box
    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": cereal.barcode, "quantity": 1})

    # But shelf vision saw 2 cereal boxes taken
    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 2,
        "confidence": 0.94,
        "timestamp": now.isoformat()
    })

    # Attempt to finalize checkout
    res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["session_status"] == "FLAGGED"
    assert data["checkout_finalized"] is False
    assert data["review_required"] is True
    assert data["decision"] == "STAFF_REVIEW_RECOMMENDED"
    assert data["verification_outcome"] == "POTENTIAL_DISCREPANCY"
    assert data["receipt"] is None


def test_checkout_flagged_session_cannot_be_re_finalized_without_review(client: TestClient):
    """
    Validation check: Direct re-finalize on a FLAGGED session must be rejected with 409 Conflict.
    """
    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_flagged", "cart_id": "cart_104"})
    session_id = sess_res.json()["id"]

    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": "8901030018241", "quantity": 1})

    # Cause discrepancy to flag session
    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 3,
        "confidence": 0.95,
        "timestamp": now.isoformat()
    })
    client.post(f"/api/v1/checkout/finalize/{session_id}")

    # Subsequent re-attempt by customer
    res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res.status_code == 409
    assert "flagged" in res.json()["detail"].lower()


def test_checkout_staff_override_approval_and_receipt(client: TestClient, db_session: Session):
    """
    Scenario 4: Store attendant reviews FLAGGED session and approves it with an audit note.
    Expected: Session transitions to COMPLETED, receipt issued, inventory decremented.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    inv = db_session.query(Inventory).filter(Inventory.product_id == cereal.id).first()
    stock_before = inv.total_store_stock

    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_override", "cart_id": "cart_105"})
    session_id = sess_res.json()["id"]
    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": cereal.barcode, "quantity": 1})

    # Flag the session with discrepancy
    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 2,
        "confidence": 0.90,
        "timestamp": now.isoformat()
    })
    client.post(f"/api/v1/checkout/finalize/{session_id}")

    # Attendant Override: APPROVE_CHECKOUT
    override_payload = {
        "staff_id": "EMP-9482",
        "override_reason": "Customer confirmed only 1 cereal item in physical bag. Second item left on shelf.",
        "action": "APPROVE_CHECKOUT"
    }
    override_res = client.post(f"/api/v1/checkout/staff-override/{session_id}", json=override_payload)
    assert override_res.status_code == 200
    data = override_res.json()

    assert data["session_status"] == "COMPLETED"
    assert data["checkout_finalized"] is True
    assert data["receipt"] is not None
    assert data["decision"] == "STAFF_OVERRIDE_APPROVED"

    # Verify inventory was decremented by 1
    db_session.refresh(inv)
    assert inv.total_store_stock == stock_before - 1


def test_checkout_staff_override_cancel(client: TestClient):
    """
    Scenario 5: Attendant cancels a flagged session.
    Expected: Session status CANCELLED, no receipt issued.
    """
    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_cancel", "cart_id": "cart_106"})
    session_id = sess_res.json()["id"]
    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": "8901030018241", "quantity": 1})

    # Flag session with discrepancy
    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 3,
        "confidence": 0.90,
        "timestamp": now.isoformat()
    })
    client.post(f"/api/v1/checkout/finalize/{session_id}")

    # Attendant Override: REJECT_CANCEL
    override_payload = {
        "staff_id": "EMP-9482",
        "override_reason": "Customer decided to put items back and leave store.",
        "action": "REJECT_CANCEL"
    }
    cancel_res = client.post(f"/api/v1/checkout/staff-override/{session_id}", json=override_payload)
    assert cancel_res.status_code == 200
    data = cancel_res.json()

    assert data["session_status"] == "CANCELLED"
    assert data["checkout_finalized"] is False
    assert data["receipt"] is None


def test_get_receipt_itemized_details(client: TestClient, db_session: Session):
    """
    Scenario 6: Retrieve receipt details, tax breakdown, and non-monetary disclaimer.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_receipt_view", "cart_id": "cart_107"})
    session_id = sess_res.json()["id"]
    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": cereal.barcode, "quantity": 2})

    now = datetime.now(timezone.utc)
    client.post("/api/v1/events/pickup", json={
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 2,
        "confidence": 0.95,
        "timestamp": now.isoformat()
    })
    client.post("/api/v1/events/sensor", json={
        "sensor_id": "SCALE-CART-107",
        "sensor_type": "WEIGHT_CART",
        "delta_weight_g": cereal.tare_weight_g * 2,
        "session_id": session_id,
        "timestamp": now.isoformat()
    })

    # Finalize
    chk_res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert chk_res.status_code == 200
    assert chk_res.json()["checkout_finalized"] is True

    # Retrieve receipt
    res = client.get(f"/api/v1/checkout/receipt/{session_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == session_id
    assert data["item_count"] == 2
    assert data["subtotal"] > 0
    assert data["grand_total"] >= data["subtotal"]
    assert len(data["items"]) == 1
    assert "DEMO NOTICE" in data["disclaimer"]


def test_checkout_inconclusive_evidence_flags_session(client: TestClient, db_session: Session):
    """
    Scenario 7: Evidence is missing or outside time window (inconclusive).
    Expected: When policy does not bypass inconclusive data, session is FLAGGED.
    """
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    sess_res = client.post("/api/v1/sessions/start", json={"user_id": "cust_inconclusive", "cart_id": "cart_108"})
    session_id = sess_res.json()["id"]

    # Only scan, no sensor or pickup evidence
    client.post("/api/v1/events/scan", json={"session_id": session_id, "barcode": cereal.barcode, "quantity": 1})

    res = client.post(f"/api/v1/checkout/finalize/{session_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["session_status"] == "FLAGGED"
    assert data["checkout_finalized"] is False
    assert data["decision"] == "STAFF_REVIEW_RECOMMENDED"
    assert data["verification_outcome"] == "INCONCLUSIVE"
