"""
SmartCart AI - Event Ingestion, Deduplication, and Timeline Tests
"""

from datetime import datetime, timezone, timedelta


def test_ingest_scan_event_success(client):
    # 1. Start Session
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "event_test_user_01", "cart_id": "cart_01"}
    )
    session_id = session_res.json()["id"]

    # 2. Ingest Scan Event
    payload = {
        "session_id": session_id,
        "barcode": "8901030018241",  # Cereal
        "quantity": 1,
        "idempotency_key": "idemp-event-test-01",
        "is_simulated": True
    }
    response = client.post("/api/v1/events/scan", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session_id
    assert data["quantity"] == 1
    assert data["is_simulated"] is True


def test_ingest_duplicate_scan_event_deduplication(client):
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "event_test_user_02", "cart_id": "cart_02"}
    )
    session_id = session_res.json()["id"]

    idemp_key = "idemp-duplicate-test-02"
    payload = {
        "session_id": session_id,
        "barcode": "8901030029312",  # Milk
        "quantity": 1,
        "idempotency_key": idemp_key,
        "is_simulated": True
    }

    # First Ingest
    res1 = client.post("/api/v1/events/scan", json=payload)
    assert res1.status_code == 201
    event_id_1 = res1.json()["id"]

    # Duplicate Ingest with same key
    res2 = client.post("/api/v1/events/scan", json=payload)
    assert res2.status_code == 200 or res2.status_code == 201
    event_id_2 = res2.json()["id"]

    # Returns same existing event ID, prevents duplicate cart row
    assert event_id_1 == event_id_2


def test_ingest_scan_invalid_barcode_returns_404(client):
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "event_test_user_03", "cart_id": "cart_03"}
    )
    session_id = session_res.json()["id"]

    payload = {
        "session_id": session_id,
        "barcode": "INVALID_BARCODE_NOT_IN_CATALOG",
        "quantity": 1
    }
    response = client.post("/api/v1/events/scan", json=payload)
    assert response.status_code == 404
    assert "does not exist in store catalogue" in response.json()["detail"]


def test_ingest_pickup_event_success(client):
    payload = {
        "shelf_id": 1,
        "detected_class": "cereal",
        "quantity_removed": 1,
        "confidence": 0.95,
        "is_simulated": True
    }
    response = client.post("/api/v1/events/pickup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["shelf_id"] == 1
    assert data["detected_class"] == "cereal"
    assert data["is_simulated"] is True


def test_ingest_sensor_event_success(client):
    payload = {
        "sensor_id": "SCALE-CART-TEST",
        "sensor_type": "WEIGHT_CART",
        "delta_weight_g": 450.0,
        "session_id": 1,
        "is_simulated": True
    }
    response = client.post("/api/v1/events/sensor", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["sensor_id"] == "SCALE-CART-TEST"
    assert data["delta_weight_g"] == 450.0
    assert data["is_simulated"] is True


def test_out_of_order_events_sorted_chronologically_in_timeline(client):
    session_res = client.post(
        "/api/v1/sessions/start",
        json={"user_id": "timeline_shopper", "cart_id": "cart_timeline"}
    )
    session_id = session_res.json()["id"]

    base_time = datetime.now(timezone.utc)

    # 1. Arrival Order 1: Scan generated at t + 10s arrives FIRST
    t_scan = base_time + timedelta(seconds=10)
    client.post(
        "/api/v1/events/scan",
        json={
            "session_id": session_id,
            "barcode": "8901030018241",
            "timestamp": t_scan.isoformat(),
            "is_simulated": True
        }
    )

    # 2. Arrival Order 2: Pickup generated at t + 2s arrives SECOND (out of order arrival)
    t_pickup = base_time + timedelta(seconds=2)
    client.post(
        "/api/v1/events/pickup",
        json={
            "shelf_id": 1,
            "detected_class": "cereal",
            "timestamp": t_pickup.isoformat(),
            "is_simulated": True
        }
    )

    # 3. Arrival Order 3: Scale event generated at t + 5s arrives THIRD
    t_sensor = base_time + timedelta(seconds=5)
    client.post(
        "/api/v1/events/sensor",
        json={
            "sensor_id": "SCALE-BAY-A1",
            "delta_weight_g": -450.0,
            "session_id": session_id,
            "timestamp": t_sensor.isoformat(),
            "is_simulated": True
        }
    )

    # Retrieve Timeline
    timeline_res = client.get(f"/api/v1/events/sessions/{session_id}/timeline")
    assert timeline_res.status_code == 200
    timeline_data = timeline_res.json()["timeline"]

    # Verify chronological sorting: Pickup (t+2) -> Sensor (t+5) -> Scan (t+10)
    event_types = [item["event_type"] for item in timeline_data]
    assert event_types == ["PICKUP", "SENSOR", "SCAN"]
