"""
SmartCart AI - Health Check Tests
"""

def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_status"] == "connected"
    assert "timestamp" in data


def test_root_metadata_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "SmartCart AI"
    assert data["documentation"] == "/docs"
