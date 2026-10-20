"""
SmartCart AI - Local Shelf-Auditing Inference CLI
Runs the SmartCart AI computer vision pipeline on a local grocery shelf image,
detects merchandise, counts visible facings, and saves an annotated visualization.
"""

import argparse
import json
import os
import sys
from backend.app.services.vision_service import ShelfAuditor


def main():
    parser = argparse.ArgumentParser(
        description="SmartCart AI Shelf Auditing CLI - Run object detection on shelf images."
    )
    parser.add_argument(
        "--image",
        type=str,
        default="backend/app/data/sample_shelves/shelf_cereal_aisle.jpg",
        help="Path to shelf image file (JPEG, PNG, WebP)"
    )
    parser.add_argument(
        "--shelf-id",
        type=int,
        default=1,
        help="Shelf bay identifier"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backend/app/data/sample_shelves/annotated_shelf.jpg",
        help="Destination path to save the annotated visualization"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Optional path to custom YOLO weights (defaults to settings.YOLO_MODEL_PATH)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Error: Specified image file '{args.image}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"   SmartCart AI — Computer Vision Shelf Auditor")
    print(f"=======================================================")
    print(f"Target Image:      {args.image}")
    print(f"Shelf Bay ID:      {args.shelf_id}")

    # Read binary bytes
    with open(args.image, "rb") as f:
        image_bytes = f.read()

    auditor = ShelfAuditor(model_path=args.model_path)
    filename = os.path.basename(args.image)

    audit_result = auditor.audit_shelf_image(
        image_bytes=image_bytes,
        filename=filename,
        shelf_id=args.shelf_id,
        return_base64=True
    )

    print("\n--- Detection Results ---")
    print(f"Audit UUID:        {audit_result.audit_id}")
    print(f"Inference Latency: {audit_result.inference_time_ms:.1f} ms")
    print(f"Total Objects:     {audit_result.total_objects_detected}")
    print(f"Detected Classes:  {audit_result.detected_counts_by_class}")
    print(f"Image Dimensions:  {audit_result.image_metadata.width}x{audit_result.image_metadata.height}")
    print(f"Quality Score:     {audit_result.image_metadata.quality_assessment} (Laplacian Var: {audit_result.image_metadata.blurriness_laplacian_var})")
    print(f"Model Framework:   {audit_result.model_metadata.framework} (Weights loaded: {audit_result.model_metadata.weights_found})")

    # If base64 was returned, decode and write to requested output path
    if audit_result.annotated_image_base64:
        import base64
        import cv2
        import numpy as np

        header, encoded = audit_result.annotated_image_base64.split(",", 1)
        data = base64.b64decode(encoded)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "wb") as f_out:
            f_out.write(data)
        print(f"\n[OK] Annotated visualization successfully saved to: {args.output}")

    print("\n--- Transparency & Engineering Limitations ---")
    print(audit_result.limitations_note)
    print("=======================================================\n")


if __name__ == "__main__":
    main()
