"""
SmartCart AI - Restocking Alerts & Inventory Intelligence Test Suite
Tests normal stock, low stock, stockout, alert deduplication, unmapped observations,
inventory separation (total vs visible stock), and attendant resolution.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.product import Product, Inventory
from backend.app.models.shelf import Shelf
from backend.app.models.alert import RestockAlert


def test_normal_stock_no_alert(client: TestClient, db_session: Session):
    """
    Scenario 1: Shelf observation shows healthy stock (e.g. 5 cereal boxes, threshold is 2).
    Expected: No new alerts generated. Total stock remains unchanged.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()
    assert shelf is not None

    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()
    inv = db_session.query(Inventory).filter(Inventory.product_id == cereal.id).first()
    original_total_stock = inv.total_store_stock

    payload = {
        "shelf_id": shelf.id,
        "observations": {"cereal": 5},
        "audit_id": "audit-normal-01"
    }

    response = client.post("/api/v1/alerts/evaluate-shelf", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["alerts_created"] == 0
    assert len(data["alerts"]) == 0
    assert len(data["unmapped_classes"]) == 0

    # Verify inventory visible stock updated, but total store stock is unmodified
    db_session.refresh(inv)
    assert inv.estimated_visible_stock == 5
    assert inv.total_store_stock == original_total_stock


def test_low_stock_alert_generation(client: TestClient, db_session: Session):
    """
    Scenario 2: Low-stock condition (1 cereal box observed, threshold is 2).
    Expected: LOW_STOCK alert generated with correct threshold and observed count.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    payload = {
        "shelf_id": shelf.id,
        "observations": {"cereal": 1},
        "audit_id": "audit-low-01",
        "evidence_metadata": {"camera_id": "CAM-BAY-A1", "confidence": 0.93}
    }

    response = client.post("/api/v1/alerts/evaluate-shelf", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["alerts_created"] == 1
    assert len(data["alerts"]) == 1
    alert = data["alerts"][0]
    assert alert["alert_type"] == "LOW_STOCK"
    assert alert["observed_count"] == 1
    assert alert["threshold"] == 2
    assert alert["is_resolved"] is False
    assert alert["product_sku"] == "CEREAL-WHEAT-01"


def test_stockout_alert_generation(client: TestClient, db_session: Session):
    """
    Scenario 3: Stockout condition (0 items observed on shelf).
    Expected: STOCKOUT alert generated.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()

    payload = {
        "shelf_id": shelf.id,
        "observations": {"cereal": 0},
        "audit_id": "audit-empty-01"
    }

    response = client.post("/api/v1/alerts/evaluate-shelf", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["alerts_created"] == 1
    assert data["alerts"][0]["alert_type"] == "STOCKOUT"
    assert data["alerts"][0]["observed_count"] == 0


def test_alert_deduplication_on_repeated_detections(client: TestClient, db_session: Session):
    """
    Scenario 4: Repeated detections do NOT spam duplicate alerts.
    Existing active alert is updated/deduplicated.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()

    payload_1 = {
        "shelf_id": shelf.id,
        "observations": {"cereal": 1},
        "audit_id": "audit-repeat-01"
    }
    resp1 = client.post("/api/v1/alerts/evaluate-shelf", json=payload_1)
    assert resp1.status_code == 200
    assert resp1.json()["alerts_created"] == 1

    alert_id_first = resp1.json()["alerts"][0]["id"]

    # Second detection 30 seconds later with count still at 1
    payload_2 = {
        "shelf_id": shelf.id,
        "observations": {"cereal": 1},
        "audit_id": "audit-repeat-02"
    }
    resp2 = client.post("/api/v1/alerts/evaluate-shelf", json=payload_2)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["alerts_created"] == 0
    assert data2["alerts_updated"] == 1
    assert data2["alerts"][0]["id"] == alert_id_first

    # Ensure total alerts count in database is still 1
    total_alerts = db_session.query(RestockAlert).count()
    assert total_alerts == 1


def test_unmapped_class_does_not_corrupt_inventory(client: TestClient, db_session: Session):
    """
    Scenario 5: Vision detector detects an unknown or unmapped object on shelf (e.g. 'umbrella').
    Expected: Object listed in unmapped_classes, no crash, no inventory corruption.
    """
    shelf = db_session.query(Shelf).first()

    payload = {
        "shelf_id": shelf.id,
        "observations": {"unsupported_exotic_fruit": 2},
        "audit_id": "audit-unmapped-01"
    }

    response = client.post("/api/v1/alerts/evaluate-shelf", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["alerts_created"] == 0
    assert "unsupported_exotic_fruit" in data["unmapped_classes"]
    assert "unmapped" in data["summary"].lower()


def test_alert_resolution_workflow(client: TestClient, db_session: Session):
    """
    Scenario 6: Store attendant resolves an open restock alert and restocks items.
    Expected: Alert marked is_resolved=True, resolution_note recorded, visible stock increased.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()
    cereal = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    # 1. Trigger low stock alert
    client.post(
        "/api/v1/alerts/evaluate-shelf",
        json={"shelf_id": shelf.id, "observations": {"cereal": 1}}
    )

    alert = db_session.query(RestockAlert).filter(RestockAlert.is_resolved == False).first()
    assert alert is not None

    # 2. Resolve alert with attendant restock of +5 units
    resolve_payload = {
        "resolution_note": "Replenished 5 boxes from warehouse backroom",
        "units_restocked": 5
    }

    patch_resp = client.patch(f"/api/v1/alerts/{alert.id}/resolve", json=resolve_payload)
    assert patch_resp.status_code == 200
    resolved_data = patch_resp.json()

    assert resolved_data["is_resolved"] is True
    assert resolved_data["resolution_note"] == "Replenished 5 boxes from warehouse backroom"
    assert resolved_data["resolved_at"] is not None

    # Verify inventory was updated
    inv = db_session.query(Inventory).filter(Inventory.product_id == cereal.id).first()
    assert inv.estimated_visible_stock == 6  # 1 (prior) + 5 (replenished)


def test_alerts_summary_stats_and_filtering(client: TestClient, db_session: Session):
    """
    Scenario 7: Test GET /alerts query filters and GET /alerts/stats/summary.
    """
    shelf = db_session.query(Shelf).first()

    # Generate one LOW_STOCK and one STOCKOUT
    client.post(
        "/api/v1/alerts/evaluate-shelf",
        json={"shelf_id": shelf.id, "observations": {"cereal": 1, "milk": 0}}
    )

    # Summary stats
    stats_resp = client.get("/api/v1/alerts/stats/summary")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_active_alerts"] == 2
    assert stats["active_stockouts"] == 1
    assert stats["active_low_stock"] == 1

    # Filter by alert_type=STOCKOUT
    list_resp = client.get("/api/v1/alerts?alert_type=STOCKOUT")
    assert list_resp.status_code == 200
    filtered = list_resp.json()
    assert len(filtered) == 1
    assert filtered[0]["alert_type"] == "STOCKOUT"
