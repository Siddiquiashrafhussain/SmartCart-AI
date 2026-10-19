"""
SmartCart AI - Product Catalogue API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.product import Product, Inventory
from backend.app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(None, description="Filter products by category"),
    search: Optional[str] = Query(None, description="Search products by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve product catalog with optional category filtering and name search.
    Includes current inventory status via joinedload.
    """
    query = db.query(Product).options(joinedload(Product.inventory))

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.offset(skip).limit(limit).all()
    logger.debug(f"Retrieved {len(products)} products (category={category}, search={search})")
    return products


@router.get("/barcode/{barcode}", response_model=ProductResponse)
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)):
    """
    Retrieve product metadata by scanned barcode (EAN-13, UPC, QR).
    Core endpoint for mobile Scan & Go camera scanner.
    """
    clean_barcode = barcode.strip()
    product = (
        db.query(Product)
        .options(joinedload(Product.inventory))
        .filter(Product.barcode == clean_barcode)
        .first()
    )

    if not product:
        logger.warning(f"Product not found for barcode: {clean_barcode}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with barcode '{clean_barcode}' does not exist in store catalogue."
        )

    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve product details by database primary key ID.
    """
    product = (
        db.query(Product)
        .options(joinedload(Product.inventory))
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """
    Register a new product in the store catalogue and initialize inventory records.
    Executed inside an ACID database transaction.
    """
    # Check for duplicate SKU or Barcode
    existing = db.query(Product).filter(
        (Product.sku == payload.sku) | (Product.barcode == payload.barcode)
    ).first()

    if existing:
        conflicting_field = "SKU" if existing.sku == payload.sku else "Barcode"
        logger.warning(f"Conflict on product creation: duplicate {conflicting_field}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with {conflicting_field} '{getattr(payload, conflicting_field.lower())}' already exists."
        )

    try:
        new_product = Product(
            sku=payload.sku,
            barcode=payload.barcode,
            name=payload.name,
            category=payload.category,
            price=payload.price,
            tare_weight_g=payload.tare_weight_g,
            description=payload.description,
            image_url=payload.image_url
        )
        db.add(new_product)
        db.flush()  # Assigns new_product.id

        # Automatically initialize Inventory record
        initial_inv = Inventory(
            product_id=new_product.id,
            total_store_stock=payload.initial_total_stock,
            estimated_visible_stock=payload.initial_visible_stock,
            safety_threshold=payload.safety_threshold
        )
        db.add(initial_inv)
        db.commit()
        db.refresh(new_product)

        logger.info(f"Created product '{new_product.name}' (ID={new_product.id}, SKU={new_product.sku})")
        return new_product

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity constraint violated during product creation."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product due to an internal server error."
        )
