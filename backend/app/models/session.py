"""
SmartCart AI - Shopping Session, Cart Items, and Scan Events ORM Models
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class ShoppingSession(Base, TimestampMixin):
    __tablename__ = "shopping_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cart_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        nullable=False,
        index=True
    )  # ACTIVE, VERIFYING, COMPLETED, FLAGGED, CANCELLED
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    scans: Mapped[list["ScanEvent"]] = relationship(
        "ScanEvent",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    verification_events: Mapped[list["backend.app.models.verification.VerificationEvent"]] = relationship(
        "VerificationEvent",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    receipt: Mapped[Optional["backend.app.models.alert.Receipt"]] = relationship(
        "Receipt",
        back_populates="session",
        uselist=False
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    session: Mapped["ShoppingSession"] = relationship("ShoppingSession", back_populates="items")
    product: Mapped["backend.app.models.product.Product"] = relationship("Product")


class ScanEvent(Base, TimestampMixin):
    __tablename__ = "scan_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    client_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    session: Mapped["ShoppingSession"] = relationship("ShoppingSession", back_populates="scans")
    product: Mapped["backend.app.models.product.Product"] = relationship("Product")
