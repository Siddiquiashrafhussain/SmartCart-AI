"""
SmartCart AI - Inventory & Stock Alert API Tests
"""

def test_list_inventory_records(client):
    response = client.get("/api/v1/inventory")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 12
    for record in data:
        assert "total_store_stock" in record
        assert "estimated_visible_stock" in record


def test_get_low_stock_alerts(client):
    response = client.get("/api/v1/inventory/alerts/low-stock")
    assert response.status_code == 200
    data = response.json()
    # At least Coca-Cola (count=0) and Oreo (count=2 <= threshold=2) trigger
    assert len(data) >= 2
    for item in data:
        assert item["estimated_visible_stock"] <= item["safety_threshold"]


def test_get_stockout_alerts(client):
    response = client.get("/api/v1/inventory/alerts/stockouts")
    assert response.status_code == 200
    data = response.json()
    # Coca-Cola is seeded with visible_stock = 0
    assert len(data) >= 1
    for item in data:
        assert item["estimated_visible_stock"] == 0


def test_update_inventory_stock(client):
    # Update product ID 1
    payload = {
        "estimated_visible_stock": 1,
        "total_store_stock": 14
    }
    response = client.patch("/api/v1/inventory/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["estimated_visible_stock"] == 1
    assert data["total_store_stock"] == 14
    assert data["last_audited_at"] is not None


def test_update_inventory_missing_product_returns_404(client):
    response = client.patch("/api/v1/inventory/9999", json={"estimated_visible_stock": 2})
    assert response.status_code == 404
