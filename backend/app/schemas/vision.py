"""
SmartCart AI - Computer Vision & Shelf Auditing Pydantic Schemas
Defines structured responses for object detection, visible item counts,
image quality metadata, and model information.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DetectionBox(BaseModel):
    box_id: int
    class_name: str = Field(..., description="Detected retail category name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox_xyxy: List[float] = Field(..., description="Pixel coordinates [x_min, y_min, x_max, y_max]")
    bbox_normalized: List[float] = Field(..., description="Normalized coordinates [x_min, y_min, x_max, y_max] in [0, 1]")


class ImageQualityMetadata(BaseModel):
    width: int
    height: int
    channels: int
    file_size_bytes: int
    blurriness_laplacian_var: float = Field(..., description="Laplacian variance (>100 is typically sharp, <50 is blurry)")
    average_brightness: float = Field(..., description="Average grayscale brightness [0 - 255]")
    quality_assessment: str = Field(..., description="SHARP, MODERATE, or BLURRY")


class ModelMetadata(BaseModel):
    model_name: str
    framework: str
    weights_path: str
    weights_found: bool
    inference_device: str
    is_mocked_or_heuristic: bool


class ShelfAuditResponse(BaseModel):
    audit_id: str
    shelf_id: Optional[int] = None
    timestamp: datetime
    image_metadata: ImageQualityMetadata
    model_metadata: ModelMetadata
    inference_time_ms: float
    total_objects_detected: int
    detected_counts_by_class: Dict[str, int]
    detections: List[DetectionBox]
    annotated_image_base64: Optional[str] = None
    annotated_image_url: Optional[str] = None
    limitations_note: str

    model_config = ConfigDict(from_attributes=True)


class VisionStatusResponse(BaseModel):
    status: str
    model_name: str
    weights_path: str
    weights_found: bool
    ultralytics_installed: bool
    opencv_version: str
    supported_classes: List[str]
    max_upload_size_mb: int
    allowed_extensions: List[str]
