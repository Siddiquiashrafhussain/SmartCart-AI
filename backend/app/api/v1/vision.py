"""
SmartCart AI - Computer Vision & Shelf Auditing API Endpoints
Accepts shelf image uploads, executes detection pipeline, returns visible item counts,
and serves annotated visualizations.
"""

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from backend.app.core.logging import logger
from backend.app.schemas.vision import ShelfAuditResponse, VisionStatusResponse
from backend.app.services.vision_service import auditor, SUPPORTED_RETAIL_CLASSES

router = APIRouter(prefix="/vision", tags=["Computer Vision & Shelf Auditing"])


@router.post("/audit-shelf", response_model=ShelfAuditResponse)
async def audit_shelf_image(
    file: UploadFile = File(..., description="Shelf image file (JPEG, PNG, or WebP)"),
    shelf_id: Optional[int] = Form(None, description="Target shelf bay ID for planogram evaluation"),
    return_annotated_base64: bool = Form(True, description="Whether to include base64 annotated image in response")
):
    """
    Upload and analyze a retail shelf bay image.
    Validates format, dimensions, and visual quality; runs object detection;
    estimates visible facings by class; and returns OpenCV annotated visualization.
    """
    filename = file.filename or "upload.jpg"
    try:
        image_bytes = await file.read()
        result = auditor.audit_shelf_image(
            image_bytes=image_bytes,
            filename=filename,
            shelf_id=shelf_id,
            return_base64=return_annotated_base64
        )
        return result
    except ValueError as ve:
        logger.warning(f"Shelf image validation failed for {filename}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Shelf image auditing error for {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing shelf image: {str(e)}"
        )


@router.get("/classes")
def list_supported_classes():
    """
    List all supported retail merchandise classes recognized by the shelf-auditing pipeline.
    """
    return {
        "supported_classes": SUPPORTED_RETAIL_CLASSES,
        "total_classes": len(SUPPORTED_RETAIL_CLASSES),
        "note": "Classes map to store inventory product categories for restock evaluation."
    }


@router.get("/status", response_model=VisionStatusResponse)
def get_vision_pipeline_status():
    """
    Retrieve operational health, model weights configuration, and detection limits.
    """
    return auditor.get_status()
