"""
SmartCart AI - Sensor Telemetry and Verification Result ORM Models
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin


class SensorEvent(Base, TimestampMixin):
    __tablename__ = "sensor_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sensor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # WEIGHT_SHELF, WEIGHT_CART
    delta_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    raw_telemetry: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


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
