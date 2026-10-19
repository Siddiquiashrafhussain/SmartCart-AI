"""
SmartCart AI - Database Seed Script
Populates deterministic products, shelves, planograms, and inventory
corresponding to the hackathon demonstration scenarios.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine
from backend.app.core.logging import logger
from backend.app.models import Base, Product, Inventory, Shelf, Planogram

DEMO_PRODUCTS = [
    {
        "sku": "CEREAL-WHEAT-01",
        "barcode": "8901030018241",
        "name": "Organic Whole Wheat Cereal",
        "category": "cereal",
        "price": 4.99,
        "tare_weight_g": 450.0,
        "description": "High-fiber whole grain morning cereal in 450g family pack.",
        "total_stock": 16,
        "visible_stock": 4,
        "threshold": 2,
    },
    {
        "sku": "MILK-WHOLE-01",
        "barcode": "8901030029312",
        "name": "Fresh Dairy Whole Milk 1L",
        "category": "milk",
        "price": 3.49,
        "tare_weight_g": 1030.0,
        "description": "Pasteurized whole milk carton with screw cap.",
        "total_stock": 24,
        "visible_stock": 6,
        "threshold": 3,
    },
    {
        "sku": "JUICE-ORANGE-01",
        "barcode": "8901030034567",
        "name": "Valencia Pure Orange Juice 500ml",
        "category": "juice",
        "price": 3.99,
        "tare_weight_g": 520.0,
        "description": "100% freshly squeezed no-added-sugar orange juice.",
        "total_stock": 18,
        "visible_stock": 3,
        "threshold": 2,
    },
    {
        "sku": "CHIPS-LAYS-01",
        "barcode": "8901030048912",
        "name": "Lay's Classic Salted Potato Chips",
        "category": "chips",
        "price": 1.99,
        "tare_weight_g": 180.0,
        "description": "Crispy golden potato chips in nitrogen-sealed bag.",
        "total_stock": 30,
        "visible_stock": 5,
        "threshold": 3,
    },
    {
        "sku": "COOKIES-OREO-01",
        "barcode": "8901030051234",
        "name": "Oreo Original Chocolate Cookies",
        "category": "cookies",
        "price": 2.49,
        "tare_weight_g": 300.0,
        "description": "Chocolate sandwich cookies with sweet vanilla creme filling.",
        "total_stock": 20,
        "visible_stock": 2,
        "threshold": 2,
    },
    {
        "sku": "TEA-LIPTON-01",
        "barcode": "8901030067890",
        "name": "Lipton Yellow Label Black Tea",
        "category": "tea",
        "price": 4.29,
        "tare_weight_g": 250.0,
        "description": "Finest blend tea bags with rich natural aroma.",
        "total_stock": 15,
        "visible_stock": 4,
        "threshold": 2,
    },
    {
        "sku": "PASTA-BARILLA-01",
        "barcode": "8901030071122",
        "name": "Barilla Penne Rigate Pasta 500g",
        "category": "pasta",
        "price": 2.19,
        "tare_weight_g": 500.0,
        "description": "Non-GMO durum wheat semolina Italian penne pasta.",
        "total_stock": 22,
        "visible_stock": 3,
        "threshold": 2,
    },
    {
        "sku": "SAUCE-PREGO-01",
        "barcode": "8901030083344",
        "name": "Prego Traditional Italian Tomato Sauce",
        "category": "tomato_sauce",
        "price": 2.89,
        "tare_weight_g": 680.0,
        "description": "Slow-cooked vine-ripened tomato sauce with sweet herbs.",
        "total_stock": 25,
        "visible_stock": 4,
        "threshold": 2,
    },
    {
        "sku": "SOUP-CAMPBELL-01",
        "barcode": "8901030095566",
        "name": "Campbell's Condensed Tomato Soup",
        "category": "canned_food",
        "price": 1.79,
        "tare_weight_g": 350.0,
        "description": "Classic pantry staple canned tomato soup.",
        "total_stock": 35,
        "visible_stock": 5,
        "threshold": 3,
    },
    {
        "sku": "BUTTER-AMUL-01",
        "barcode": "8901030107788",
        "name": "Amul Pasteurized Butter 500g",
        "category": "dairy_butter",
        "price": 3.25,
        "tare_weight_g": 510.0,
        "description": "Pure cream salted butter block.",
        "total_stock": 28,
        "visible_stock": 5,
        "threshold": 2,
    },
    {
        "sku": "BEV-COKE-01",
        "barcode": "8901030119900",
        "name": "Coca-Cola Original Taste 500ml",
        "category": "beverage_soda",
        "price": 1.50,
        "tare_weight_g": 525.0,
        "description": "Carbonated soft drink bottle.",
        "total_stock": 16,
        "visible_stock": 0,  # Simulated initial Stockout scenario
        "threshold": 2,
    },
    {
        "sku": "NOODLES-MAGGI-01",
        "barcode": "8901030122211",
        "name": "Maggi 2-Minute Masala Instant Noodles",
        "category": "instant_noodles",
        "price": 0.99,
        "tare_weight_g": 140.0,
        "description": "Favorite masala flavored instant snack noodles.",
        "total_stock": 40,
        "visible_stock": 8,
        "threshold": 3,
    },
]

DEMO_SHELVES = [
    {"aisle_number": 1, "shelf_level": 1, "bay_code": "BAY-A1", "camera_id": "CAM-01-A1"},
    {"aisle_number": 1, "shelf_level": 2, "bay_code": "BAY-A2", "camera_id": "CAM-01-A2"},
    {"aisle_number": 1, "shelf_level": 3, "bay_code": "BAY-A3", "camera_id": "CAM-01-A3"},
    {"aisle_number": 2, "shelf_level": 1, "bay_code": "BAY-B1", "camera_id": "CAM-02-B1"},
    {"aisle_number": 2, "shelf_level": 2, "bay_code": "BAY-B2", "camera_id": "CAM-02-B2"},
    {"aisle_number": 2, "shelf_level": 3, "bay_code": "BAY-B3", "camera_id": "CAM-02-B3"},
    {"aisle_number": 3, "shelf_level": 1, "bay_code": "BAY-C1", "camera_id": "CAM-03-C1"},
    {"aisle_number": 3, "shelf_level": 2, "bay_code": "BAY-C2", "camera_id": "CAM-03-C2"},
    {"aisle_number": 3, "shelf_level": 3, "bay_code": "BAY-C3", "camera_id": "CAM-03-C3"},
]


def seed_database(db: Session = None):
    """
    Seed database with initial catalog, inventory, and shelf planograms.
    """
    should_close = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        should_close = True

    try:
        logger.info("Checking database seed status...")
        existing_count = db.query(Product).count()
        if existing_count > 0:
            logger.info(f"Database already seeded with {existing_count} products. Skipping.")
            return

        logger.info("Seeding shelves...")
        shelves_map = {}
        for s_data in DEMO_SHELVES:
            shelf = Shelf(
                aisle_number=s_data["aisle_number"],
                shelf_level=s_data["shelf_level"],
                bay_code=s_data["bay_code"],
                camera_id=s_data["camera_id"]
            )
            db.add(shelf)
            db.flush()
            shelves_map[s_data["bay_code"]] = shelf

        logger.info("Seeding products & inventory...")
        for p_data in DEMO_PRODUCTS:
            product = Product(
                sku=p_data["sku"],
                barcode=p_data["barcode"],
                name=p_data["name"],
                category=p_data["category"],
                price=p_data["price"],
                tare_weight_g=p_data["tare_weight_g"],
                description=p_data["description"]
            )
            db.add(product)
            db.flush()

            inventory = Inventory(
                product_id=product.id,
                total_store_stock=p_data["total_stock"],
                estimated_visible_stock=p_data["visible_stock"],
                safety_threshold=p_data["threshold"],
                last_audited_at=datetime.now(timezone.utc)
            )
            db.add(inventory)

        db.commit()
        logger.info(f"Seeding completed successfully: {len(DEMO_PRODUCTS)} products, {len(DEMO_SHELVES)} shelves.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_database()
