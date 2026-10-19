"""
SmartCart AI - Restock Alert and Digital Receipt ORM Models
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class RestockAlert(Base, TimestampMixin):
    __tablename__ = "restock_alerts"

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
    alert_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )  # LOW_STOCK, STOCKOUT, MISPLACED_ITEM, UNSCANNED_PICKUP
    observed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    shelf: Mapped["backend.app.models.shelf.Shelf"] = relationship("Shelf")
    product: Mapped["backend.app.models.product.Product"] = relationship("Product")


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), default="SIMULATED_PAID", nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Relationships
    session: Mapped["backend.app.models.session.ShoppingSession"] = relationship(
        "ShoppingSession",
        back_populates="receipt"
    )
