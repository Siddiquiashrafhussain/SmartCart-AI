"""
SmartCart AI - Sensor Telemetry, Shelf Pickups, and Verification Result ORM Models
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class SensorEvent(Base, TimestampMixin):
    __tablename__ = "sensor_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sensor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # WEIGHT_SHELF, WEIGHT_CART
    delta_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("shopping_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    shelf_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("shelves.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    raw_telemetry: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ShelfPickupEvent(Base, TimestampMixin):
    """
    Vision-derived observation of an item being physically removed from a shelf bay.
    """
    __tablename__ = "shelf_pickup_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shelf_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shelves.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    detected_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    quantity_removed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    shelf: Mapped["backend.app.models.shelf.Shelf"] = relationship("Shelf")
    product: Mapped[Optional["backend.app.models.product.Product"]] = relationship("Product")


class VerificationEvent(Base, TimestampMixin):
    __tablename__ = "verification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    verdict: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )  # CONSISTENT, UNCERTAIN, MISMATCH
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_summary: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    session: Mapped["backend.app.models.session.ShoppingSession"] = relationship(
        "ShoppingSession",
        back_populates="verification_events"
    )
