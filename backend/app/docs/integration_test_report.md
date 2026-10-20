# SmartCart AI — Integration Test Report & Hackathon Demo Walkthrough
**Date**: October 20, 2026  
**Auditor**: Senior QA Engineer, Site Reliability Engineer & Hackathon Demo Lead  
**Test Suite Status**: 61 Passed, 0 Failed, 2 Warnings (100% Pass Rate)

---

## 1. Executive Summary

SmartCart AI was subjected to an end-to-end integration audit across all subsystems:
- Product Catalogue & Stock Separation (Authoritative Store Stock vs Visible Shelf Facings)
- IoT Sensor Ingestion & Timestamp Correlation
- YOLO / OpenCV Computer Vision Pipeline & Laplacian Blur Diagnostics
- Threshold Monitoring & Deduplicated Restock Alerts
- Staff Admin Web Dashboard & Real-Time WebSocket Telemetry
- Multi-Modal Verification Engine & Decoupled Checkout Decisions
- Idempotent Digital Receipt Issuance & Attendant Overrides

All 61 automated tests passed synchronously in **1.47 seconds**. Zero mocked successes or fabricated benchmark metrics were accepted.

---

## 2. Test Execution Results Matrix

| Test Suite Module | Tests Run | Pass | Fail | Coverage Scope |
| :--- | :---: | :---: | :---: | :--- |
| `backend/tests/test_health.py` | 2 | 2 | 0 | Service liveness, database ping probe (`SELECT 1`) |
| `backend/tests/test_products.py` | 7 | 7 | 0 | Barcode lookup, SKU catalogue pagination, price validation |
| `backend/tests/test_inventory.py` | 5 | 5 | 0 | Authoritative stock vs visible shelf stock separation, stock levels |
| `backend/tests/test_sessions.py` | 5 | 5 | 0 | Session start, cart item add/remove/update, spend computation |
| `backend/tests/test_events.py` | 6 | 6 | 0 | Scan, camera pickup, weight load-cell event ingestion |
| `backend/tests/test_vision.py` | 7 | 7 | 0 | OpenCV decoding, Laplacian variance blur, brightness, fallback detector |
| `backend/tests/test_alerts.py` | 7 | 7 | 0 | Low-stock, stockout, alert deduplication, attendant resolution |
| `backend/tests/test_verification.py` | 8 | 8 | 0 | Multi-modal correlation ($\tau=15\text{s}$, $\pm 50\text{g}$), missing vs contradictory evidence |
| `backend/tests/test_dashboard.py` | 5 | 5 | 0 | Static assets, HTML dashboard at `/dashboard`, WebSocket handshake & ping/pong |
| `backend/tests/test_checkout.py` | 9 | 9 | 0 | Empty cart guard, auto-approve checkout, idempotency, discrepancy blocks, receipts |
| **TOTAL** | **61** | **61** | **0** | **100% Pass Rate** |

---

## 3. Verified System Services & Endpoints

### 3.1 Backend Application Gateway
- **FastAPI Core**: Running on Python 3.13.14 / Starlette.
- **Root Endpoint**: `GET /` &rarr; metadata, docs link, health probe, dashboard URL.
- **Interactive Documentation**: Swagger UI at `/docs` and ReDoc at `/redoc`.
- **Health Check**: `GET /api/v1/health` &rarr; JSON `{ "status": "ok", "database_status": "connected" }`.

### 3.2 Staff Admin Dashboard & Real-Time Streams
- **Web Interface**: `GET /dashboard` (or redirect via `GET /admin`).
- **Design System**: Zero-build dark glassmorphic CSS3 with modern typography.
- **WebSocket Gateway**: `ws://<host>:<port>/api/v1/ws/dashboard`.
  - Initial handshake: `{ "event_type": "HANDSHAKE_ESTABLISHED", "protocol_version": "1.0" }`.
  - Heartbeat response: Ping &rarr; `{ "event_type": "PONG" }`.
  - Push broadcasts: `ALERT_TRIGGERED`, `ALERT_RESOLVED`, `SESSION_VERIFIED`, `CHECKOUT_FINALIZED`, `CHECKOUT_FLAGGED`.

---

## 4. Reproducible Hackathon Demonstration Scenarios

To demonstrate SmartCart AI live to hackathon judges, execute the following verified scenarios:

### Scenario 1: Normal Purchase (Consistent Multi-Modal Evidence)
- **Command**: `python -m backend.app.scripts.simulate_events --scenario normal_purchase --verify`
- **Telemetry Injected**: Barcode scan for Cereal, camera pickup of cereal from Shelf #1 ($t=0$), cart scale $+450\text{g}$ ($t=2\text{s}$).
- **Engine Output**: `outcome = NO_DISCREPANCY_DETECTED`, `checkout_decision = AUTO_APPROVE`, `confidence = 95.0%`.
- **Checkout Outcome**: Digital receipt issued (`SIMULATED_PAID`), transaction hash generated, store inventory decremented by 1 unit.

### Scenario 2: Unscanned Merchandise Pickup
- **Command**: `python -m backend.app.scripts.simulate_events --scenario unscanned_pickup --verify`
- **Telemetry Injected**: Camera observes pickup of cereal from Shelf #1, shelf scale drops $-450\text{g}$, but shopper NEVER scans barcode.
- **Engine Output**: `outcome = POTENTIAL_DISCREPANCY`, `checkout_decision = STAFF_REVIEW_RECOMMENDED`, `confidence = 30.0%`.
- **Checkout Outcome**: Auto-approval blocked. Session flagged for attendant assistance.

### Scenario 3: Product Mismatch / Class Conflict
- **Command**: `python -m backend.app.scripts.simulate_events --scenario product_mismatch --verify`
- **Telemetry Injected**: Camera observes removal of Black Tea from Shelf #6, but shopper scans Instant Noodles.
- **Engine Output**: `outcome = POTENTIAL_DISCREPANCY`, `checkout_decision = STAFF_REVIEW_RECOMMENDED`, `confidence = 35.0%`.
- **Checkout Outcome**: Auto-approval blocked. Attendant alerted to product mismatch.

### Scenario 4: Quantity Conflict
- **Command**: `python -m backend.app.scripts.simulate_events --scenario quantity_mismatch --verify`
- **Telemetry Injected**: Camera observes 2 soup cans taken, but shopper only scans 1 can.
- **Engine Output**: `outcome = POTENTIAL_DISCREPANCY`, `checkout_decision = STAFF_REVIEW_RECOMMENDED`, `confidence = 35.0%`.
- **Checkout Outcome**: Auto-approval blocked. Attendant dashboard displays exact quantity discrepancy (+1 unrecorded).

### Scenario 5: Temporal Synchronization Drift (Inconclusive)
- **Command**: `python -m backend.app.scripts.simulate_events --scenario delayed_evidence --verify`
- **Telemetry Injected**: Pickup occurs at $t=0$, but barcode scan occurs 45 seconds later ($\Delta t = 45\text{s} > \tau = 15\text{s}$).
- **Engine Output**: `outcome = INCONCLUSIVE`, `checkout_decision = STAFF_REVIEW_RECOMMENDED`, `confidence = 60.0%`.
- **Checkout Outcome**: System acknowledges temporal drift; routes to attendant spot check without accusing shopper.

### Scenario 6: Missing Hardware Corroboration (Graceful Degradation)
- **Command**: `python -m backend.app.scripts.simulate_events --scenario missing_evidence --verify`
- **Telemetry Injected**: Shopper scans barcode on a shelf without cameras or weight sensors.
- **Engine Output**: `outcome = INCONCLUSIVE`, `checkout_decision = STAFF_REVIEW_RECOMMENDED`, `confidence = 70.0%`.
- **Audit Explanation**: Engine explicitly distinguishes missing hardware from contradicting evidence.

---

## 5. Computer Vision Pipeline Audit & Transparency Disclosures

1. **Hardware Fallback Mode**: When optional PyTorch/Ultralytics weights are omitted, the `ShelfAuditor` executes OpenCV spatial and blur assessments (`Laplacian variance > 100.0` threshold for sharpness) without raising exceptions.
2. **Visible Shelf vs Store Stock**: Camera detections calculate visible facings only. Total warehouse/store stock remains isolated in authoritative database ledgers.
3. **Occlusion & Lighting**: 2D front-facing cameras cannot detect items stacked behind front rows; cellophane glare can degrade confidence. Attendants treat all warnings as inventory audit tasks rather than customer accusations.

---

## 6. Known Limitations & Roadmap

- **Simulated Payment**: Digital receipts are issued with `payment_status="SIMULATED_PAID"`. No real credit card or payment gateway is integrated.
- **Single-Node WebSocket**: The WebSocket manager uses in-memory connection pooling suitable for single-store edge gateways. Multi-store enterprise scaling requires a Redis Pub/Sub backplane.
