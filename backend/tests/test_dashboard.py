"""
SmartCart AI - Staff Admin Dashboard & Real-Time WebSocket Tests
Tests HTML dashboard delivery, static assets, admin redirect, WebSocket connection lifecycle,
heartbeat ping/pong, and real-time push events.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.models.shelf import Shelf
from backend.app.models.alert import RestockAlert


def test_dashboard_html_view(client: TestClient):
    """
    Ensure the staff admin dashboard HTML interface is accessible at /dashboard.
    """
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SmartCart AI" in response.text
    assert "Store Staff & Operations Console" in response.text
    assert "ws-badge" in response.text


def test_admin_redirect(client: TestClient):
    """
    Ensure /admin redirects staff smoothly to /dashboard.
    """
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert response.headers["location"] == "/dashboard"


def test_static_assets_served(client: TestClient):
    """
    Ensure CSS design system and JavaScript client bundle are served.
    """
    css_res = client.get("/static/dashboard/styles.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers["content-type"]

    js_res = client.get("/static/dashboard/app.js")
    assert js_res.status_code == 200
    assert any(ct in js_res.headers["content-type"] for ct in ["javascript", "text/plain"])


def test_websocket_connection_and_heartbeat(client: TestClient):
    """
    Ensure WebSocket connection can be established, receives connection confirmation,
    and responds with PONG upon receiving ping.
    """
    with client.websocket_connect("/api/v1/ws/dashboard") as websocket:
        # Initial greeting event
        init_data = websocket.receive_json()
        assert init_data["event_type"] == "HANDSHAKE_ESTABLISHED"
        assert init_data["protocol_version"] == "1.0"

        # Test heartbeat
        websocket.send_text("ping")
        pong_data = websocket.receive_json()
        assert pong_data["event_type"] == "PONG"


def test_websocket_broadcast_on_alert_resolution(client: TestClient, db_session: Session):
    """
    Ensure that when an attendant resolves an alert via REST API,
    the active WebSocket client receives the ALERT_RESOLVED broadcast event in real-time.
    """
    shelf = db_session.query(Shelf).filter(Shelf.bay_code == "BAY-A1").first()
    product = db_session.query(Product).filter(Product.sku == "CEREAL-WHEAT-01").first()

    alert = RestockAlert(
        shelf_id=shelf.id,
        product_id=product.id,
        alert_type="LOW_STOCK",
        observed_count=1,
        threshold=2,
        is_resolved=False
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    with client.websocket_connect("/api/v1/ws/dashboard") as websocket:
        # Discard initial connection greeting
        init_data = websocket.receive_json()
        assert init_data["event_type"] == "HANDSHAKE_ESTABLISHED"

        # Resolve alert via REST endpoint
        patch_payload = {
            "resolution_note": "Restocked 5 units from storeroom",
            "units_restocked": 5
        }
        res = client.patch(f"/api/v1/alerts/{alert.id}/resolve", json=patch_payload)
        assert res.status_code == 200

        # Receive real-time broadcast via WebSocket
        ws_event = websocket.receive_json()
        assert ws_event["event_type"] == "ALERT_RESOLVED"
        assert ws_event["alert"]["id"] == alert.id
        assert ws_event["alert"]["resolution_note"] == "Restocked 5 units from storeroom"
