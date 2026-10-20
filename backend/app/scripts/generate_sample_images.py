"""
SmartCart AI - Sample Shelf Image Generator
Creates realistic grocery shelf scenes using OpenCV for local demonstration,
testing, and computer vision auditing without external internet dependencies.
"""

import os
import cv2
import numpy as np


def create_shelf_background(width=800, height=600):
    """Draws a clean retail shelf bay with metal back panel and shelf racks."""
    img = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)

    # Shelf rack horizontal bars
    cv2.rectangle(img, (0, 180), (width, 200), (120, 120, 120), -1)  # Top shelf
    cv2.rectangle(img, (0, 380), (width, 400), (120, 120, 120), -1)  # Middle shelf
    cv2.rectangle(img, (0, 570), (width, 590), (100, 100, 100), -1)  # Bottom shelf

    # Shelf label strips
    cv2.rectangle(img, (0, 195), (width, 210), (0, 140, 220), -1)
    cv2.rectangle(img, (0, 395), (width, 410), (0, 140, 220), -1)
    cv2.rectangle(img, (0, 585), (width, 600), (0, 140, 220), -1)

    # Vertical shelf side uprights
    cv2.rectangle(img, (10, 0), (25, height), (90, 90, 90), -1)
    cv2.rectangle(img, (width - 25, 0), (width - 10, height), (90, 90, 90), -1)

    return img


def draw_cereal_box(img, x, y, width=70, height=130, label="Cereal"):
    """Draws a front-facing cereal box."""
    # Box body
    cv2.rectangle(img, (x, y), (x + width, y + height), (40, 160, 240), -1)
    cv2.rectangle(img, (x, y), (x + width, y + height), (20, 100, 180), 2)

    # Decorative header
    cv2.rectangle(img, (x + 5, y + 10), (x + width - 5, y + 40), (20, 100, 220), -1)
    cv2.putText(img, label[:6], (x + 8, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # Center graphic bowl
    cv2.circle(img, (x + width // 2, y + 80), 20, (255, 255, 255), -1)
    cv2.circle(img, (x + width // 2, y + 80), 16, (0, 200, 255), -1)


def draw_milk_carton(img, x, y, width=60, height=140, label="Milk 1L"):
    """Draws a milk carton with triangular roof."""
    # Main carton
    cv2.rectangle(img, (x, y + 20), (x + width, y + height), (230, 216, 173), -1)
    cv2.rectangle(img, (x, y + 20), (x + width, y + height), (160, 140, 100), 2)

    # Gable top
    pts = np.array([
        [x, y + 20],
        [x + width // 2, y],
        [x + width, y + 20]
    ], np.int32)
    cv2.fillPoly(img, [pts], (210, 190, 150))
    cv2.polylines(img, [pts], True, (160, 140, 100), 2)

    # Blue banner
    cv2.rectangle(img, (x + 5, y + 40), (x + width - 5, y + 70), (200, 100, 20), -1)
    cv2.putText(img, label[:5], (x + 8, y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)


def draw_juice_bottle(img, x, y, width=50, height=120, label="Juice"):
    """Draws a juice bottle."""
    # Bottle neck
    cv2.rectangle(img, (x + 15, y), (x + width - 15, y + 25), (255, 255, 255), -1)
    # Bottle cap
    cv2.rectangle(img, (x + 12, y), (x + width - 12, y + 8), (0, 100, 255), -1)
    # Body
    cv2.rectangle(img, (x, y + 25), (x + width, y + height), (30, 144, 255), -1)
    cv2.rectangle(img, (x, y + 25), (x + width, y + height), (10, 100, 200), 2)
    # Label
    cv2.rectangle(img, (x + 4, y + 50), (x + width - 4, y + 85), (255, 255, 255), -1)
    cv2.putText(img, label[:5], (x + 6, y + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 1)


def generate_sample_images(output_dir="backend/app/data/sample_shelves"):
    """Generates 3 test shelf images corresponding to normal, low stock, and stockout conditions."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Normal Fully Stocked Shelf
    shelf_normal = create_shelf_background()
    # Top shelf: 4 cereal boxes
    for i in range(4):
        draw_cereal_box(shelf_normal, 60 + i * 90, 50, label="Cereal")
    # Middle shelf: 3 milk cartons, 2 juice bottles
    for i in range(3):
        draw_milk_carton(shelf_normal, 60 + i * 80, 240, label="Milk")
    for i in range(2):
        draw_juice_bottle(shelf_normal, 360 + i * 70, 260, label="Juice")

    normal_path = os.path.join(output_dir, "shelf_cereal_aisle.jpg")
    cv2.imwrite(normal_path, shelf_normal)

    # 2. Low Stock Shelf (Only 1 cereal box remaining)
    shelf_low = create_shelf_background()
    draw_cereal_box(shelf_low, 60, 50, label="Cereal")  # Only 1 facing left
    low_path = os.path.join(output_dir, "shelf_low_stock.jpg")
    cv2.imwrite(low_path, shelf_low)

    # 3. Completely Empty Shelf (Stockout scenario)
    shelf_empty = create_shelf_background()
    empty_path = os.path.join(output_dir, "shelf_empty.jpg")
    cv2.imwrite(empty_path, shelf_empty)

    print(f"[OK] Generated sample shelf images in '{output_dir}':")
    print(f"  - {normal_path} (Fully stocked)")
    print(f"  - {low_path} (Low stock: 1 cereal box)")
    print(f"  - {empty_path} (Empty shelf / stockout)")


if __name__ == "__main__":
    generate_sample_images()
