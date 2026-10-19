"""
SmartCart AI - Shelf and Planogram ORM Models
"""

from typing import Optional
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class Shelf(Base, TimestampMixin):
    __tablename__ = "shelves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aisle_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shelf_level: Mapped[int] = mapped_column(Integer, nullable=False)
    bay_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    camera_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    planograms: Mapped[list["Planogram"]] = relationship(
        "Planogram",
        back_populates="shelf",
        cascade="all, delete-orphan"
    )


class Planogram(Base, TimestampMixin):
    __tablename__ = "planograms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shelf_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shelves.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    compartment_code: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_x_start: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized [0.0 - 1.0]
    slot_x_end: Mapped[float] = mapped_column(Float, nullable=False)    # Normalized [0.0 - 1.0]
    expected_facings: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    min_safety_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    # Relationships
    shelf: Mapped["Shelf"] = relationship("Shelf", back_populates="planograms")
    product: Mapped["backend.app.models.product.Product"] = relationship("Product", back_populates="planograms")
