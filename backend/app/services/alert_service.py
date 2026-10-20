"""
SmartCart AI - Inventory Monitoring & Restocking Alert Service
Translates shelf visual observations into inventory intelligence and actionable alerts.
Guarantees separation of observed visible shelf counts from authoritative store inventory,
deduplicates recurring alerts, and tracks alert lifecycles.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload

from backend.app.core.logging import logger
from backend.app.models.product import Product, Inventory
from backend.app.models.shelf import Shelf, Planogram
from backend.app.models.alert import RestockAlert
from backend.app.schemas.alert import (
    RestockAlertResponse,
    ShelfEvaluationResponse,
    AlertsSummaryStatsResponse,
)


class InventoryAlertService:
    """
    Core business service for shelf observation processing and restock alert management.
    """

    def __init__(self, db: Session):
        self.db = db

    def _format_alert_response(self, alert: RestockAlert) -> RestockAlertResponse:
        """Formats an ORM RestockAlert into response schema with eager-loaded metadata."""
        product_sku = alert.product.sku if alert.product else None
        product_name = alert.product.name if alert.product else None
        shelf_bay = alert.shelf.bay_code if alert.shelf else None

        return RestockAlertResponse(
            id=alert.id,
            shelf_id=alert.shelf_id,
            product_id=alert.product_id,
            product_sku=product_sku,
            product_name=product_name,
            shelf_bay_code=shelf_bay,
            alert_type=alert.alert_type,
            observed_count=alert.observed_count,
            threshold=alert.threshold,
            is_resolved=alert.is_resolved,
            resolved_at=alert.resolved_at,
            resolution_note=alert.resolution_note,
            evidence_metadata=alert.evidence_metadata,
            created_at=alert.created_at,
            updated_at=alert.resolved_at or alert.created_at,
        )

    def evaluate_shelf_observations(
        self,
        shelf_id: int,
        observations: Dict[str, int],
        audit_id: Optional[str] = None,
        evidence_metadata: Optional[Dict[str, Any]] = None
    ) -> ShelfEvaluationResponse:
        """
        Processes visible object counts observed by computer vision on a shelf bay.
        Compares counts against safety thresholds and updates inventory records.
        Deduplicates existing active alerts to avoid notification spamming.
        """
        shelf = (
            self.db.query(Shelf)
            .options(joinedload(Shelf.planograms).joinedload(Planogram.product))
            .filter(Shelf.id == shelf_id)
            .first()
        )

        if not shelf:
            raise ValueError(f"Shelf ID {shelf_id} not found in store planogram database.")

        now = datetime.now(timezone.utc)
        alerts_created = 0
        alerts_updated = 0
        affected_alerts: List[RestockAlert] = []
        unmapped_classes: List[str] = []

        # Iterate over observed class counts (e.g. {"cereal": 1, "milk": 0})
        for class_name, count in observations.items():
            clean_class = class_name.strip().lower()

            # 1. Product Association Logic
            # First attempt: match via shelf's configured planogram
            target_product: Optional[Product] = None
            for p in shelf.planograms:
                if p.product and (
                    p.product.category.lower() == clean_class or
                    clean_class in p.product.category.lower() or
                    p.product.category.lower() in clean_class
                ):
                    target_product = p.product
                    break

            # Second attempt: catalog category search if not specifically in planogram
            if not target_product:
                target_product = (
                    self.db.query(Product)
                    .filter(Product.category.ilike(f"%{clean_class}%"))
                    .first()
                )

            # If observation cannot be reliably associated with a known product
            if not target_product:
                unmapped_classes.append(class_name)
                logger.warning(
                    f"Shelf observation '{class_name}' on shelf {shelf_id} cannot be mapped to a known product. "
                    f"Observation skipped without modifying store inventory."
                )
                continue

            # 2. Update Inventory Visible Stock (Distinct from Total Store Stock)
            inv = (
                self.db.query(Inventory)
                .filter(Inventory.product_id == target_product.id)
                .first()
            )

            safety_threshold = 2
            if inv:
                # Update visible stock estimate; DO NOT overwrite authoritative total_store_stock
                inv.estimated_visible_stock = count
                inv.last_audited_at = now
                safety_threshold = inv.safety_threshold
            else:
                # Create initial inventory record if missing
                inv = Inventory(
                    product_id=target_product.id,
                    total_store_stock=10,  # default placeholder total
                    estimated_visible_stock=count,
                    safety_threshold=2,
                    last_audited_at=now
                )
                self.db.add(inv)

            # 3. Threshold Evaluation
            needed_alert_type: Optional[str] = None
            if count == 0:
                needed_alert_type = "STOCKOUT"
            elif count <= safety_threshold:
                needed_alert_type = "LOW_STOCK"

            # 4. Alert Deduplication & Status Tracking
            active_alert = (
                self.db.query(RestockAlert)
                .filter(
                    RestockAlert.shelf_id == shelf_id,
                    RestockAlert.product_id == target_product.id,
                    RestockAlert.is_resolved == False
                )
                .first()
            )

            # Combine evidence metadata
            meta = {
                "audit_id": audit_id,
                "detected_class": class_name,
                "observed_count": count,
                "safety_threshold": safety_threshold,
                "audited_at": now.isoformat(),
            }
            if evidence_metadata:
                meta.update(evidence_metadata)

            if needed_alert_type is not None:
                if active_alert:
                    # Deduplicate: update existing active alert rather than creating a duplicate
                    active_alert.alert_type = needed_alert_type
                    active_alert.observed_count = count
                    active_alert.threshold = safety_threshold
                    active_alert.evidence_metadata = meta
                    alerts_updated += 1
                    affected_alerts.append(active_alert)
                    logger.info(
                        f"Deduplicated existing active alert #{active_alert.id} for product {target_product.name}: "
                        f"type={needed_alert_type}, observed={count}"
                    )
                else:
                    # Create new alert
                    new_alert = RestockAlert(
                        shelf_id=shelf_id,
                        product_id=target_product.id,
                        alert_type=needed_alert_type,
                        observed_count=count,
                        threshold=safety_threshold,
                        is_resolved=False,
                        evidence_metadata=meta
                    )
                    self.db.add(new_alert)
                    alerts_created += 1
                    affected_alerts.append(new_alert)
                    logger.info(
                        f"Generated new {needed_alert_type} alert on shelf {shelf_id} for product '{target_product.name}' "
                        f"(count={count}, threshold={safety_threshold})"
                    )
            else:
                # Stock is healthy (> threshold)
                # If an active alert existed previously, auto-resolve it as restocked
                if active_alert:
                    active_alert.is_resolved = True
                    active_alert.resolved_at = now
                    active_alert.resolution_note = f"Auto-resolved: shelf visual count ({count}) is above safety threshold ({safety_threshold})."
                    logger.info(f"Auto-resolved restock alert #{active_alert.id} as shelf stock returned to normal.")

        self.db.commit()

        # Refresh affected alerts for output formatting
        for a in affected_alerts:
            self.db.refresh(a)

        # Broadcast real-time WebSocket update for store staff dashboard
        try:
            from backend.app.core.websocket import ws_manager
            for a in affected_alerts:
                ws_manager.broadcast_sync({
                    "event_type": "ALERT_TRIGGERED",
                    "timestamp": now.isoformat(),
                    "alert": self._format_alert_response(a).model_dump(mode="json")
                })
        except Exception as e:
            logger.debug(f"WebSocket broadcast skipped: {e}")

        summary_msg = (
            f"Evaluated {len(observations)} shelf observations on Shelf #{shelf_id}. "
            f"Created {alerts_created} new alert(s), updated/deduplicated {alerts_updated} alert(s)."
        )
        if unmapped_classes:
            summary_msg += f" Note: {len(unmapped_classes)} observation(s) were unmapped ({', '.join(unmapped_classes)})."

        return ShelfEvaluationResponse(
            shelf_id=shelf_id,
            total_observations=len(observations),
            alerts_created=alerts_created,
            alerts_updated=alerts_updated,
            alerts=[self._format_alert_response(a) for a in affected_alerts],
            unmapped_classes=unmapped_classes,
            summary=summary_msg
        )

    def list_alerts(
        self,
        shelf_id: Optional[int] = None,
        product_id: Optional[int] = None,
        alert_type: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[RestockAlertResponse]:
        """Lists restock alerts with optional filtering and pagination."""
        query = (
            self.db.query(RestockAlert)
            .options(
                joinedload(RestockAlert.product),
                joinedload(RestockAlert.shelf)
            )
        )

        if shelf_id is not None:
            query = query.filter(RestockAlert.shelf_id == shelf_id)
        if product_id is not None:
            query = query.filter(RestockAlert.product_id == product_id)
        if alert_type is not None:
            query = query.filter(RestockAlert.alert_type == alert_type.upper())
        if is_resolved is not None:
            query = query.filter(RestockAlert.is_resolved == is_resolved)

        alerts = query.order_by(RestockAlert.created_at.desc()).offset(skip).limit(limit).all()
        return [self._format_alert_response(a) for a in alerts]

    def get_alert_by_id(self, alert_id: int) -> RestockAlertResponse:
        """Retrieves a single alert by ID."""
        alert = (
            self.db.query(RestockAlert)
            .options(
                joinedload(RestockAlert.product),
                joinedload(RestockAlert.shelf)
            )
            .filter(RestockAlert.id == alert_id)
            .first()
        )
        if not alert:
            raise ValueError(f"Restock alert with ID {alert_id} not found.")

        return self._format_alert_response(alert)

    def resolve_alert(
        self,
        alert_id: int,
        resolution_note: Optional[str] = None,
        units_restocked: Optional[int] = None
    ) -> RestockAlertResponse:
        """
        Attendant workflow: Acknowledges and resolves an open restock alert.
        Optionally updates estimated visible stock if units_restocked is specified.
        """
        alert = (
            self.db.query(RestockAlert)
            .options(
                joinedload(RestockAlert.product),
                joinedload(RestockAlert.shelf)
            )
            .filter(RestockAlert.id == alert_id)
            .first()
        )
        if not alert:
            raise ValueError(f"Restock alert with ID {alert_id} not found.")

        now = datetime.now(timezone.utc)
        alert.is_resolved = True
        alert.resolved_at = now
        alert.resolution_note = resolution_note or "Resolved by store attendant"

        # Update visible stock if attendant reported replenishment count
        if units_restocked is not None and units_restocked > 0:
            inv = self.db.query(Inventory).filter(Inventory.product_id == alert.product_id).first()
            if inv:
                inv.estimated_visible_stock += units_restocked
                inv.last_audited_at = now
                logger.info(f"Inventory visible stock increased by {units_restocked} upon alert #{alert.id} resolution.")

        self.db.commit()
        self.db.refresh(alert)

        # Broadcast real-time WebSocket update for store staff dashboard
        try:
            from backend.app.core.websocket import ws_manager
            ws_manager.broadcast_sync({
                "event_type": "ALERT_RESOLVED",
                "timestamp": now.isoformat(),
                "alert": self._format_alert_response(alert).model_dump(mode="json")
            })
        except Exception as e:
            logger.debug(f"WebSocket broadcast skipped: {e}")

        logger.info(f"Restock alert #{alert.id} marked as resolved.")
        return self._format_alert_response(alert)

    def get_summary_stats(self) -> AlertsSummaryStatsResponse:
        """Computes high-level store restocking intelligence metrics."""
        total_active = self.db.query(RestockAlert).filter(RestockAlert.is_resolved == False).count()
        stockouts = (
            self.db.query(RestockAlert)
            .filter(RestockAlert.is_resolved == False, RestockAlert.alert_type == "STOCKOUT")
            .count()
        )
        low_stock = (
            self.db.query(RestockAlert)
            .filter(RestockAlert.is_resolved == False, RestockAlert.alert_type == "LOW_STOCK")
            .count()
        )
        total_resolved = self.db.query(RestockAlert).filter(RestockAlert.is_resolved == True).count()

        return AlertsSummaryStatsResponse(
            total_active_alerts=total_active,
            active_stockouts=stockouts,
            active_low_stock=low_stock,
            total_resolved_alerts=total_resolved
        )
