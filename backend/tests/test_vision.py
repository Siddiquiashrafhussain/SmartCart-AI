"""
SmartCart AI - Computer Vision & Shelf Auditing Test Suite
Tests image validation, OpenCV preprocessing, deterministic detection mocking,
visible item count estimation, annotated image rendering, and REST endpoints.
"""

import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.services.vision_service import ShelfAuditor, SUPPORTED_RETAIL_CLASSES
from backend.app.schemas.vision import ShelfAuditResponse


def _create_test_image_bytes(width=300, height=300, color=(100, 150, 200), fmt=".jpg") -> bytes:
    """Creates in-memory image bytes for testing."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 200), (0, 0, 255), -1)
    cv2.putText(img, "TEST", (60, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    success, encoded = cv2.imencode(fmt, img)
    assert success
    return encoded.tobytes()


def test_vision_status_endpoint(client: TestClient):
    """
    Test GET /api/v1/vision/status returns model config and operational state.
    """
    response = client.get("/api/v1/vision/status")
    assert response.status_code == 200
    data = response.json()

    assert "model_name" in data
    assert "weights_found" in data
    assert "opencv_version" in data
    assert "supported_classes" in data
    assert data["max_upload_size_mb"] == 10
    assert "jpg" in data["allowed_extensions"]


def test_supported_classes_endpoint(client: TestClient):
    """
    Test GET /api/v1/vision/classes returns grocery categories.
    """
    response = client.get("/api/v1/vision/classes")
    assert response.status_code == 200
    data = response.json()

    assert data["total_classes"] == len(SUPPORTED_RETAIL_CLASSES)
    assert "cereal" in data["supported_classes"]
    assert "milk" in data["supported_classes"]


def test_audit_shelf_endpoint_success(client: TestClient):
    """
    Test POST /api/v1/vision/audit-shelf with valid image.
    """
    img_bytes = _create_test_image_bytes()
    files = {"file": ("shelf_bay.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {"shelf_id": 1, "return_annotated_base64": True}

    response = client.post("/api/v1/vision/audit-shelf", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert "audit_id" in res
    assert res["shelf_id"] == 1
    assert res["image_metadata"]["width"] == 300
    assert res["image_metadata"]["height"] == 300
    assert res["image_metadata"]["quality_assessment"] in ["SHARP", "MODERATE", "BLURRY"]
    assert "data:image/jpeg;base64," in res["annotated_image_base64"]
    assert "AI Vision Pipeline Limitations" in res["limitations_note"]


def test_audit_shelf_reject_invalid_extension(client: TestClient):
    """
    Test rejection of unsupported file extensions (e.g. .pdf or .txt).
    """
    files = {"file": ("malicious_file.exe", io.BytesIO(b"dummy binary data"), "application/octet-stream")}
    response = client.post("/api/v1/vision/audit-shelf", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_audit_shelf_reject_corrupted_image(client: TestClient):
    """
    Test rejection of invalid/corrupted bytes with .jpg extension.
    """
    corrupted_bytes = b"not an image at all, just plain text"
    files = {"file": ("broken.jpg", io.BytesIO(corrupted_bytes), "image/jpeg")}
    response = client.post("/api/v1/vision/audit-shelf", files=files)
    assert response.status_code == 400
    assert "Failed to decode image data" in response.json()["detail"]


def test_audit_shelf_reject_empty_file(client: TestClient):
    """
    Test rejection of 0-byte uploaded file.
    """
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    response = client.post("/api/v1/vision/audit-shelf", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_deterministic_mocked_detection_pipeline():
    """
    Unit test ShelfAuditor using deterministic mocked detections.
    Ensures exact count calculation, bounding boxes, and base64 rendering.
    """
    auditor = ShelfAuditor()
    img_bytes = _create_test_image_bytes(width=400, height=400)

    mock_dets = [
        {"class_name": "cereal", "confidence": 0.94, "bbox_xyxy": [20, 30, 100, 180]},
        {"class_name": "cereal", "confidence": 0.91, "bbox_xyxy": [110, 30, 190, 180]},
        {"class_name": "cereal", "confidence": 0.89, "bbox_xyxy": [200, 30, 280, 180]},
        {"class_name": "milk", "confidence": 0.92, "bbox_xyxy": [50, 210, 130, 370]},
        {"class_name": "milk", "confidence": 0.95, "bbox_xyxy": [150, 210, 230, 370]},
    ]

    result = auditor.audit_shelf_image(
        image_bytes=img_bytes,
        filename="test_mock.jpg",
        shelf_id=2,
        return_base64=True,
        mock_detections=mock_dets
    )

    assert result.total_objects_detected == 5
    assert result.detected_counts_by_class == {"cereal": 3, "milk": 2}
    assert len(result.detections) == 5
    assert result.detections[0].class_name == "cereal"
    assert result.detections[0].confidence == 0.94
    assert result.detections[0].bbox_normalized == [0.05, 0.075, 0.25, 0.45]
    assert result.annotated_image_base64.startswith("data:image/jpeg;base64,")
    assert "Occlusion" in result.limitations_note
