"""
SmartCart AI - Shopping Session & Cart Scanning Tests
"""

def test_start_session_lifecycle(client):
    payload = {"user_id": "shopper_test_01", "cart_id": "cart_hw_01"}
    response = client.post("/api/v1/sessions/start", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["user_id"] == "shopper_test_01"
    assert data["items"] == []
    assert data["subtotal"] == 0.0


def test_scan_item_adds_to_cart(client):
    # 1. Start Session
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "shopper_02", "cart_id": "cart_02"}
    )
    session_id = session_res.json()["id"]

    # 2. Scan Organic Whole Wheat Cereal (Barcode: 8901030018241, Price: 4.99)
    scan_res = client.post(
        "/api/v1/sessions/scan",
        json={"session_id": session_id, "barcode": "8901030018241"}
    )
    assert scan_res.status_code == 200
    cart_data = scan_res.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["quantity"] == 1
    assert cart_data["subtotal"] == 4.99

    # 3. Scan same item second time -> quantity increments
    scan_res_2 = client.post(
        "/api/v1/sessions/scan",
        json={"session_id": session_id, "barcode": "8901030018241"}
    )
    assert scan_res_2.status_code == 200
    cart_data_2 = scan_res_2.json()
    assert cart_data_2["items"][0]["quantity"] == 2
    assert cart_data_2["subtotal"] == 9.98


def test_scan_idempotency_prevents_duplicate_events(client):
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "shopper_03", "cart_id": "cart_03"}
    )
    session_id = session_res.json()["id"]

    idempotency_key = "idemp-test-uuid-12345"

    # First Scan
    res1 = client.post(
        "/api/v1/sessions/scan",
        json={
            "session_id": session_id,
            "barcode": "8901030029312",
            "idempotency_key": idempotency_key
        }
    )
    assert res1.status_code == 200
    assert res1.json()["total_items"] == 1

    # Retried duplicate Scan with same key
    res2 = client.post(
        "/api/v1/sessions/scan",
        json={
            "session_id": session_id,
            "barcode": "8901030029312",
            "idempotency_key": idempotency_key
        }
    )
    assert res2.status_code == 200
    assert res2.json()["total_items"] == 1  # Not incremented


def test_scan_unrecognized_barcode_returns_404(client):
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "shopper_04", "cart_id": "cart_04"}
    )
    session_id = session_res.json()["id"]

    scan_res = client.post(
        "/api/v1/sessions/scan",
        json={"session_id": session_id, "barcode": "0000000000000"}
    )
    assert scan_res.status_code == 404
    assert "does not match" in scan_res.json()["detail"]
