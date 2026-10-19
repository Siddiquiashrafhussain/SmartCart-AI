"""
SmartCart AI - Product Catalogue API Tests
"""

def test_list_products_returns_seeded_items(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 12
    first_item = data[0]
    assert "sku" in first_item
    assert "barcode" in first_item
    assert "inventory" in first_item


def test_list_products_with_category_filter(client):
    response = client.get("/api/v1/products?category=cereal")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(item["category"] == "cereal" for item in data)


def test_get_product_by_valid_barcode(client):
    # Barcode for Organic Whole Wheat Cereal from seed
    barcode = "8901030018241"
    response = client.get(f"/api/v1/products/barcode/{barcode}")
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "CEREAL-WHEAT-01"
    assert data["price"] == 4.99
    assert data["tare_weight_g"] == 450.0


def test_get_product_by_missing_barcode_returns_404(client):
    missing_barcode = "9999999999999"
    response = client.get(f"/api/v1/products/barcode/{missing_barcode}")
    assert response.status_code == 404
    data = response.json()
    assert "does not exist" in data["detail"]


def test_create_product_success(client):
    payload = {
        "sku": "SNACK-ALMONDS-01",
        "barcode": "8901030999999",
        "name": "Roasted Salted California Almonds 200g",
        "category": "nuts_snacks",
        "price": 5.99,
        "tare_weight_g": 210.0,
        "description": "Premium slow-roasted California almonds.",
        "initial_total_stock": 20,
        "initial_visible_stock": 6,
        "safety_threshold": 3
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "SNACK-ALMONDS-01"
    assert data["inventory"]["total_store_stock"] == 20
    assert data["inventory"]["estimated_visible_stock"] == 6


def test_create_product_duplicate_sku_returns_409(client):
    payload = {
        "sku": "CEREAL-WHEAT-01",  # Existing SKU in seed
        "barcode": "8901030888888",
        "name": "Duplicate SKU Test",
        "category": "cereal",
        "price": 3.99,
        "tare_weight_g": 300.0
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_product_invalid_price_returns_422(client):
    payload = {
        "sku": "INVALID-PRICE-01",
        "barcode": "8901030777777",
        "name": "Invalid Price Test",
        "category": "cereal",
        "price": -4.99,  # Invalid negative price
        "tare_weight_g": 300.0
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 422
