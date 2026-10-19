"""
SmartCart AI - Product Catalogue and Inventory ORM Models
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    barcode: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    tare_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    inventory: Mapped[Optional["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan"
    )
    planograms: Mapped[list["Planogram"]] = relationship(
        "Planogram",
        back_populates="product",
        cascade="all, delete-orphan"
    )


class Inventory(Base, TimestampMixin):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    total_store_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_visible_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    last_audited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory")
