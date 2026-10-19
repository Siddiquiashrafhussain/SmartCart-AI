# SmartCart AI

> **Intelligent Scan & Go, Shelf Auditing & Loss Prevention**  
> *Shop Smarter. Verify Instantly. Restock Proactively.*

---

### Hackathon Metadata & Project Identification

| Parameter | Details |
| :--- | :--- |
| **Hackathon** | **Computer Vision AI Hackathon 2026** (Organized by **E-Cell IIT Bombay** & **Everseen**) |
| **Track / Problem Statement** | **Problem Statement 2: Mobile Scan and Go – Checkout Anywhere Loss Prevention** |
| **Project Title** | **SmartCart AI** |
| **Team Name** | **LIFTOFF** (Team Leader: Ashraf Hussain Siddiqui) |
| **Institution** | **Universal SkillTech University (USTU)** |
| **Submission Status** | Final Submitted (Oct 10, 2026) |
| **Presentation Deck** | [Google Drive Presentation](https://drive.google.com/file/d/1SlEyEoBlBbtSVJINsRr_drxD9l10xcfI/view?usp=drive_link) |

---

## Executive Summary

**SmartCart AI** is a multimodal retail intelligence platform that unifies computer vision, mobile Scan & Go self-checkout, automated shelf auditing, and sensor event correlation into a cohesive loss-prevention and inventory optimization ecosystem.

In modern retail environments, self-checkout and mobile Scan & Go implementations suffer from a fundamental architectural flaw: **a barcode scan records only a claimed intent to purchase, with no automated validation of physical reality.** At the same time, floor staff struggle with manual shelf audits, resulting in unobserved stockouts, misplaced SKUs, phantom inventory, and delayed replenishment.

SmartCart AI bridges physical shelf interactions with digital shopping carts. Using fixed shelf cameras running pretrained Ultralytics YOLO object detection models, spatial planogram matching algorithms, and time-synchronized event correlation (fusing barcode scans, visual observations, and load-cell telemetry), the platform:
1. Audits shelf stock levels and detects out-of-stock (OOS) conditions and misplaced items in real time.
2. Validates mobile shopper cart interactions against physical shelf removals using configurable confidence windows.
3. Classifies checkout transactions into verified, uncertain (requiring staff audit), or discrepant states.
4. Streams proactive restocking alerts and audit events to a centralized store administration console via WebSockets.

---

## Technology Stack

The SmartCart AI system architecture is engineered using proven, modular open-source technologies:

```
                  +----------------------------------------------+
                  |            SmartCart AI Platform             |
                  +----------------------------------------------+
                                         |
     +-------------------+---------------+---------------+--------------------+
     |                   |                               |                    |
     v                   v                               v                    v
[ Mobile Client ]   [ Backend API ]             [ Vision Pipeline ]   [ Data Layer ]
  Flutter 3.x         FastAPI (Python 3.13)       OpenCV 5.x            PostgreSQL 16
  Dart 3.x            Uvicorn ASGI Server         Ultralytics YOLO      SQLAlchemy / Alembic
  Mobile Barcode      WebSockets (Real-time)      Spatial Planogram     Redis (Proposed Cache)
```

| Component | Technology | Target Version | Implementation Role |
| :--- | :--- | :--- | :--- |
| **Mobile Application** | Flutter & Dart | Flutter 3.29+ / Dart 3.7+ | Cross-platform mobile Scan & Go customer client, camera barcode scanner, local cart state |
| **Backend REST API** | FastAPI / Python | Python 3.13 / FastAPI 0.141+ | Asynchronous service gateway, validation schemas, business rules, cart & checkout transactions |
| **Real-Time Streaming** | WebSockets | `websockets` 17.1+ / ASGI | Low-latency duplex event delivery to store admin dashboard for instant alerts and audits |
| **Computer Vision Engine** | OpenCV & Ultralytics | OpenCV 5.0+ / YOLOv8-YOLOv11 | Image preprocessing, product bounding box regression, class classification, gap analysis |
| **Primary Relational DB** | PostgreSQL | PostgreSQL 15+ / 16+ | ACID-compliant storage for catalog, inventory, planograms, sessions, logs, and audit trails |
| **Sensor Telemetry Layer** | ESP32 / C++ / Python Mock | ESP-IDF / MicroPython / Mock | Cart/shelf load-cell sensor telemetry ingestion (simulated via Python event generator) |
| **Admin Console** | Next.js / TypeScript | Next.js 15+ / React 19 / Tailwind | Store manager console for live inventory monitoring, alert triage, and discrepancy reviews |

---

## Table of Contents

1. [Hackathon Metadata & Project Identification](#hackathon-metadata--project-identification)
2. [Executive Summary](#executive-summary)
3. [Technology Stack](#technology-stack)
4. [Problem Statement & Operational Value](#problem-statement--operational-value)
5. [High-Level System Architecture](#high-level-system-architecture)
   - [Mermaid 1: High-Level System Architecture](#mermaid-1-high-level-system-architecture)
   - [Architectural Layers Breakdown](#architectural-layers-breakdown)
6. [Repository Structure & Service Organization](#repository-structure--service-organization)
7. [Shelf-Auditing & Computer Vision Pipeline](#shelf-auditing--computer-vision-pipeline)
   - [Mermaid 2: Shelf-Auditing Pipeline](#mermaid-2-shelf-auditing-pipeline)
   - [Detection, Counting & Planogram Comparison](#detection-counting--planogram-comparison)
   - [Environmental Factors & Physical Constraints](#environmental-factors--physical-constraints)
8. [Computer Vision & AI Model Deep-Dive](#computer-vision--ai-model-deep-dive)
9. [Mobile Scan & Go and Verification Workflow](#mobile-scan--go-and-verification-workflow)
   - [Mermaid 3: Scan & Go Secondary Verification](#mermaid-3-scan--go-secondary-verification)
   - [The Core Philosophy: Scan != Physical Interaction](#the-core-philosophy-scan--physical-interaction)
10. [Event & Data Flow Sequence](#event--data-flow-sequence)
    - [Mermaid 4: Sequence of Telemetry & Verification Flow](#mermaid-4-sequence-of-telemetry--verification-flow)
11. [Feature Inventory & Implementation Status](#feature-inventory--implementation-status)
12. [Database Schema & Data Model](#database-schema--data-model)
13. [REST & WebSocket API Specification](#rest--websocket-api-specification)
14. [Discrepancy Detection & Verification Logic](#discrepancy-detection--verification-logic)
15. [Reproducible Hackathon Demo Scenarios](#reproducible-hackathon-demo-scenarios)
16. [Local Setup & Developer Guide](#local-setup--developer-guide)
17. [Environment Configuration](#environment-configuration)
18. [Visual Assets & Interface Mockups](#visual-assets--interface-mockups)
19. [Testing, Security & Reliability](#testing-security--reliability)
20. [Current Limitations & Future Roadmap](#current-limitations--future-roadmap)
21. [Team LIFTOFF & Institutional Affiliation](#team-liftoff--institutional-affiliation)
22. [License & Acknowledgements](#license--acknowledgements)

---

## Problem Statement & Operational Value

Mobile Scan & Go shopping delivers unparalleled consumer convenience, eliminating checkout queues and accelerating in-store visits. However, self-checkout without automated physical safeguards exposes retailers to unprecedented levels of operational shrinkage, inventory distortion, and checkout discrepancies.

### The Retail Trilemma

```
         +-------------------------------------------------------+
         |               The Retail Shrink Trilemma              |
         +-------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v                                                   v
[ Checkout Friction vs. Loss ]                    [ Visibility vs. Labor Cost ]
- Frictionless: Easy shrinkage / walkouts          - Frequent audits: High labor expense
- Heavy security: Alienates honest shoppers       - No audits: Ghost inventory / stockouts
```

| Retail Challenge | SmartCart AI Technical Capability | Expected Operational Benefit |
| :--- | :--- | :--- |
| **1. Unscanned Physical Item Pickups**<br>Shoppers pick up physical items from shelves and place them into bags without scanning barcodes. | **Spatial Shelf-Vision Correlation Engine**<br>Detects item count drops on specific shelf zones within time window $\tau$ and cross-references active cart scan events. | Flags unaccounted pickups for non-intrusive staff verification before shopper leaves store. |
| **2. Barcode / Product Swapping**<br>Shopper scans an inexpensive product barcode (e.g., $1 instant noodles) but takes a premium SKU (e.g., $15 imported meat). | **Multi-Modal Verification Engine**<br>Correlates the scanned SKU class with the visual class detected by shelf cameras and weight differential recorded by sensors. | Prevents intentional or accidental barcode swapping; generates an immediate `Product Mismatch` alert. |
| **3. Undetected Shelf Out-of-Stocks (OOS)**<br>Products run out on shelves while inventory systems indicate units in stock (backroom vs. on-shelf disparity). | **Automated YOLO Shelf Auditing**<br>Periodic optical inspection computes visible shelf occupancy against minimum safety thresholds. | Triggers automated restock notifications directly to floor associates, cutting out-of-stock durations. |
| **4. Misplaced Merchandise**<br>Customers abandon chilled or high-value items on incorrect ambient shelves, leading to spoilage or customer confusion. | **Planogram Grid Mapping**<br>Maps bounding box centroids $(x, y)$ to expected shelf compartments $(Aisle_i, Shelf_j, Compartment_k)$. | Identifies misplaced items and directs staff to return them to designated locations. |
| **5. False Accusations & Customer Alienation**<br>Overzealous loss-prevention stops honest shoppers who encountered scanner errors or accidental double-scans. | **Three-Tiered Classification (Consistent / Uncertain / Mismatch)**<br>Rules separate ambiguous sensor noise from deliberate discrepancies. | Directs ambiguous events to polite customer service checks rather than accusatory interventions. |

> [!IMPORTANT]
> **Ethical Principle:** In SmartCart AI, a discrepancy is treated strictly as an **operational signal for human-in-the-loop review**, never as definitive proof of malicious theft. Camera occlusions, bad barcode prints, and shopper indecision can generate false alerts. The system minimizes false positives by aggregating multi-source evidence.

---

## High-Level System Architecture

SmartCart AI is built on a loosely coupled, client-server service architecture designed for low-latency ingest of multi-sensor telemetry, asynchronous computer vision batching, and real-time state synchronization.

### Mermaid 1: High-Level System Architecture

```mermaid
flowchart TD
    %% Subgraphs for Logical Architecture
    subgraph INPUT_LAYER["1. Input & Telemetry Layer"]
        CAM["Shelf Overhead Cameras\n(RTSP / Video Frames)"]
        MOBILE_APP["Shopper Mobile Client\n(Flutter / Dart Scanner)"]
        WEIGHT_SENSORS["Load-Cell Scales\n(ESP32 / Simulated Telemetry)"]
        SIM_BED["Simulation Testbed\n(Synthetic Event Generator)"]
    end

    subgraph INGEST_GATEWAY["2. Communication & Gateway Layer"]
        REST_GW["FastAPI API Gateway\n(REST Endpoints: /api/v1)"]
        WS_GW["FastAPI WebSocket Server\n(/ws/alerts, /ws/cart)"]
    end

    subgraph PROCESSING_LAYER["3. Processing & Analytics Layer"]
        CV_ENGINE["Computer Vision Pipeline\n- OpenCV Frame Preprocessing\n- Ultralytics YOLO Object Detection\n- Shelf Occupancy Estimator"]
        PLANOGRAM_SVC["Planogram Engine\n- Digital Shelf Layout Maps\n- Expected Compartment Coordinates\n- Misplaced SKU Identifier"]
        CORRELATION_ENGINE["Event Correlation & Verification Engine\n- Time-Window Synchronization (dt <= tau)\n- Spatial-to-Session Attribution\n- Sensor Fusion & Weight Deltas"]
    end

    subgraph APPLICATION_LAYER["4. Application Business Logic"]
        CART_SVC["Virtual Cart Service\n(Session Lifecycle & Totals)"]
        VERIFY_SVC["Checkout Verification Engine\n(Consistent / Uncertain / Mismatch)"]
        RESTOCK_SVC["Restocking & Replenishment Service\n(Threshold Monitors & Stockout Triggers)"]
        RECEIPT_SVC["Digital Receipt Generator\n(Cryptographic Transaction Record)"]
    end

    subgraph PERSISTENCE_LAYER["5. Persistence Layer (PostgreSQL)"]
        DB[(PostgreSQL 16 Relational DB\n- products, shelves, planograms\n- inventory, shopping_sessions\n- cart_items, scan_events\n- sensor_events, verification_events\n- restock_alerts, receipts)]
    end

    subgraph DASHBOARD_LAYER["6. Presentation & Staff Review"]
        ADMIN_WEB["Store Admin Dashboard\n(Next.js / TypeScript / Tailwind)\n- Live Shelf Heatmaps\n- Restock Alerts Queue\n- Discrepancy Audit Triage"]
    end

    %% Wiring Inputs to Gateway
    CAM -->|Image Batch / POST /cv/audit| REST_GW
    MOBILE_APP -->|Scans, Cart Actions / REST| REST_GW
    WEIGHT_SENSORS -.->|Telemetry / POST /sensors| REST_GW
    SIM_BED -.->|Synthetic Payloads| REST_GW

    %% Gateway to Processing
    REST_GW --> CV_ENGINE
    REST_GW --> CART_SVC
    REST_GW --> CORRELATION_ENGINE

    %% Processing Interactions
    CV_ENGINE <--> PLANOGRAM_SVC
    CV_ENGINE -->|Visible Counts & Gaps| CORRELATION_ENGINE
    CV_ENGINE -->|Low Stock / Misplaced Events| RESTOCK_SVC
    
    CART_SVC -->|Scanned SKUs & Timestamps| CORRELATION_ENGINE
    CORRELATION_ENGINE -->|Fused Evidence Matrix| VERIFY_SVC
    VERIFY_SVC -->|Status: Verified| RECEIPT_SVC

    %% Persistence
    CV_ENGINE --- DB
    CART_SVC --- DB
    CORRELATION_ENGINE --- DB
    RESTOCK_SVC --- DB
    RECEIPT_SVC --- DB

    %% Alerts & Realtime Push
    RESTOCK_SVC -->|Push Low Stock Alerts| WS_GW
    VERIFY_SVC -->|Push Discrepancies| WS_GW
    WS_GW ==>|Live WebSocket Feed| ADMIN_WEB
    REST_GW <-->|Management REST Queries| ADMIN_WEB

    classDef input fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef gateway fill:#ede7f6,stroke:#512da8,stroke-width:2px;
    classDef processing fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef db fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
    classDef ui fill:#e0f2f1,stroke:#00796b,stroke-width:2px;

    class CAM,MOBILE_APP,WEIGHT_SENSORS,SIM_BED input;
    class REST_GW,WS_GW gateway;
    class CV_ENGINE,PLANOGRAM_SVC,CORRELATION_ENGINE processing;
    class CART_SVC,VERIFY_SVC,RESTOCK_SVC,RECEIPT_SVC app;
    class DB db;
    class ADMIN_WEB ui;
```

### Architectural Layers Breakdown

1. **Input Layer**: Handles heterogeneous data sources including edge camera frames, mobile barcode scan events via customer smartphones, load-cell sensor telemetry (via ESP32 or simulated test drivers), and synthetic demo events.
2. **Processing Layer**: Houses the computationally intensive algorithms: OpenCV image normalization, YOLO product detection, spatial planogram coordinate matching, and the temporal correlation engine ($\Delta t \le \tau$) fusing multi-sensor signals.
3. **Application Layer**: Contains domain services governing shopping sessions, virtual cart calculations, rule-based verification policies, automated replenishment triggers, and receipt rendering.
4. **Data Layer**: Centralized PostgreSQL database maintaining ACID transactional guarantees for inventory state changes, shopping session lifecycles, and tamper-evident verification audit logs.
5. **Communication Layer**: Dual-channel interface comprising synchronous FastAPI REST endpoints (CRUD, scan logging, checkout) and asynchronous WebSockets (real-time store associate alerts).

---

## Repository Structure & Service Organization

The repository is organized following clean architectural separation of concerns, isolating machine learning inference, backend API services, mobile client code, and telemetry simulation scripts:

```
SmartCart AI/
├── README.md                      # Comprehensive Hackathon Architecture & Guide
├── .env.example                   # Environment configuration template
├── LICENSE                        # MIT Open-Source License
├── docker-compose.yml             # Container orchestration (PostgreSQL, FastAPI, Web)
│
├── backend/                       # FastAPI Backend Application Service
│   ├── app/
│   │   ├── main.py                # FastAPI application entrypoint & ASGI router
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic BaseSettings environment config
│   │   │   └── security.py        # Token validation & session cryptography
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── router.py      # Main v1 endpoint aggregation
│   │   │   │   ├── products.py    # Product catalog lookup & barcode mapping
│   │   │   │   ├── cart.py        # Virtual cart session mutations
│   │   │   │   ├── audit.py       # Shelf image upload & YOLO invocation
│   │   │   │   ├── verify.py      # Multimodal correlation evaluation
│   │   │   │   └── alerts.py      # Restocking alert query & resolution
│   │   ├── services/
│   │   │   ├── cart_service.py    # Cart business logic & total computations
│   │   │   ├── correlation.py     # Time-windowed sensor-event correlation engine
│   │   │   ├── planogram.py       # 2D spatial coordinate mapping & compartment logic
│   │   │   └── notification.py    # WebSocket connection manager & broadcast broker
│   │   ├── models/                # SQLAlchemy ORM relational models
│   │   │   ├── product.py
│   │   │   ├── shelf.py
│   │   │   ├── session.py
│   │   │   └── alert.py
│   │   └── schemas/               # Pydantic request/response validation schemas
│   │       ├── cart_schema.py
│   │       ├── scan_schema.py
│   │       └── audit_schema.py
│   ├── tests/                     # Backend integration and unit tests
│   │   ├── test_cart.py
│   │   ├── test_correlation.py
│   │   └── test_api_endpoints.py
│   └── requirements.txt           # Python backend dependencies
│
├── cv_pipeline/                   # Computer Vision & Inference Modules
│   ├── detector.py                # Ultralytics YOLO loader & inference runner
│   ├── preprocessor.py            # OpenCV CLAHE normalization & resizing
│   ├── planogram_matcher.py       # Centroid-to-slot spatial mapping logic
│   ├── weights/
│   │   └── yolov8n.pt             # Pretrained YOLO model weights
│   └── sample_images/             # Evaluation & sample retail shelf images
│       ├── shelf_normal.jpg
│       ├── shelf_low_stock.jpg
│       └── shelf_misplaced.jpg
│
├── mobile/                        # Customer Scan & Go Mobile Application
│   ├── pubspec.yaml               # Flutter package manifest & dependencies
│   ├── lib/
│   │   ├── main.dart              # Flutter application entrypoint
│   │   ├── core/                  # Theme, network client, and constants
│   │   ├── features/
│   │   │   ├── scanner/           # Camera barcode scanner view & controller
│   │   │   ├── cart/              # Virtual cart view & item quantity mutator
│   │   │   └── checkout/          # Verification status & digital receipt view
│   │   └── services/              # API repository client & WebSocket listener
│
├── dashboard/                     # Store Administration Web Console (Next.js)
│   ├── package.json               # Node.js dependencies
│   ├── src/
│   │   ├── app/                   # Next.js App Router pages (Inventory, Alerts, Review)
│   │   ├── components/            # Real-time alert cards & shelf heatmap overlays
│   │   └── hooks/                 # WebSocket hook for live store event stream
│
└── scripts/                       # Developer Tooling & Simulation Suites
    ├── seed_database.py           # Populates demo products, shelves & planograms
    ├── simulate_events.py         # Simulates end-to-end shopping & sensor streams
    └── evaluate_vision.py         # Runs detection benchmarking across test images
```

---

## Shelf-Auditing & Computer Vision Pipeline

The computer vision subsystem performs automated optical auditing of retail shelf facings. It transforms unstructured visual frames into structured inventory metrics: visible product counts, shelf gap assessments, out-of-stock detections, and planogram compliance.

### Mermaid 2: Shelf-Auditing Pipeline

```mermaid
flowchart TD
    START(["1. Camera Frame Ingest\n(Periodic Trigger / RTSP Stream)"]) --> VAL{"2. Frame Validation\n- Valid dimensions?\n- Brightness / blur OK?"}
    
    VAL -->|Fail: Corrupt / Degraded| ERR_LOG["Log Frame Error\nRequest Camera Calibration"]
    VAL -->|Pass: Valid Frame| PREPROC["3. Image Preprocessing\n- Resize to 640x640\n- Color space conversion (BGR to RGB)\n- CLAHE contrast enhancement"]
    
    PREPROC --> YOLO["4. Ultralytics YOLO Inference\n(Pretrained weights: best.pt / yolov8n.pt)\nBounding Box Regression & Class Scoring"]
    
    YOLO --> FILTER{"5. Confidence Threshold\nConfidence >= 0.45?"}
    FILTER -->|Discard Below Threshold| NOISE["Drop Low-Confidence Detections"]
    FILTER -->|Retain| DETECTIONS["6. Extracted Detections\n- Class IDs & Names\n- Confidence Scores (e.g. 0.89)\n- Normalized Bounding Boxes [x1, y1, x2, y2]"]
    
    DETECTIONS --> SPATIAL["7. Spatial Grid & Planogram Matching\nMap bounding box centroids (cx, cy) to\nShelf Compartments (Aisle, Shelf, Slot)"]
    
    SPATIAL --> COMPARISON{"8. Planogram Comparison\nDetected SKU == Expected SKU?"}
    
    COMPARISON -->|Mismatch Detected| MISPLACED["Generate Misplaced Item Event\n(e.g., Tea found in Coffee Slot)"]
    COMPARISON -->|Match Confirmed| COUNT["9. Compartment Count Aggregation\nCompute Visible Units per Product"]
    
    COUNT --> THRESHOLD{"10. Safety Stock Check\nVisible Count <= Min Threshold?"}
    
    THRESHOLD -->|Count == 0| STOCKOUT["Trigger Critical Stockout Alert\n(Priority: HIGH)"]
    THRESHOLD -->|Count <= Threshold| LOW_STOCK["Trigger Low-Stock Restocking Alert\n(Priority: MEDIUM)"]
    THRESHOLD -->|Count > Threshold| NORMAL["Update Visible Shelf State\nStatus: NORMAL"]
    
    STOCKOUT --> DISPATCH["11. Dispatch to Store Dashboard\n& Event Correlation Engine"]
    LOW_STOCK --> DISPATCH
    MISPLACED --> DISPATCH
    NORMAL --> PERSIST["12. Persist Shelf Observation\nto PostgreSQL DB"]
    DISPATCH --> PERSIST

    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:1px;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:1px;
    classDef alert fill:#ffebee,stroke:#c62828,stroke-width:1px;
    classDef success fill:#e8f8f5,stroke:#2e7d32,stroke-width:1px;

    class START,PREPROC,YOLO,DETECTIONS,SPATIAL,COUNT,PERSIST process;
    class VAL,FILTER,COMPARISON,THRESHOLD decision;
    class ERR_LOG,NOISE,MISPLACED,STOCKOUT,LOW_STOCK alert;
    class NORMAL,DISPATCH success;
```

### Detection, Counting & Planogram Comparison

1. **Object Detection**: The pipeline utilizes pretrained YOLO models configured for retail packaging geometries. The model identifies product categories (e.g., Cereal, Milk, Juice, Chips, Cookies, Tea, Pasta, Canned Food).
2. **Visible Count Estimation**: The system clusters bounding boxes by spatial intersection over union (IoU) and compartment partitions to determine the front-facing item count.
3. **Planogram Comparison**: Each shelf bay is calibrated with expected 2D spatial compartments:
   $$\text{Compartment}(Aisle, Shelf, Slot) \rightarrow \text{Expected\_SKU}, \text{Min\_Threshold}$$
   If a detected bounding box centroid $(c_x, c_y)$ falls within Slot $B3$ (configured for Tea) but classifies as Cereal, a `Misplaced Item` event is emitted.
4. **Auditing Reality Check**:
   $$\text{Visible Shelf Count} \neq \text{Total Store Inventory}$$
   Computer vision estimates front-facing display quantity. Total store inventory includes units in backrooms, top overstock risers, and items currently held in transit by other shoppers in the store.

### Environmental Factors & Physical Constraints

In real-world retail deployments, computer vision performance is strictly bounded by physical and optical limitations:
* **Occlusion**: Units positioned in secondary and tertiary rows behind the front-facing items are obscured from overhead cameras.
* **Lighting Variations**: Fluorescent glare, seasonal sunlight angles, or poorly lit lower shelves reduce detection confidence scores.
* **Packaging Homogeneity**: Brand variants sharing near-identical packaging (e.g., Diet Coke vs. Coke Zero, different flavors of chips) require high-resolution input or fine-grained models to distinguish accurately.
* **Camera Angles & Perspective Distortion**: Extreme oblique angles at the edges of wide-angle camera lenses distort bounding box centroids relative to shelf dividers.

---

## Computer Vision & AI Model Deep-Dive

### Model Specifications & Architecture

| Parameter | Specification |
| :--- | :--- |
| **Model Architecture** | Ultralytics YOLOv8 / YOLOv11 (Nano `yolov8n` for edge; Small `yolov8s` for server) |
| **Input Resolution** | $640 \times 640$ pixels (RGB 3-channel, normalized $[0, 1]$) |
| **Inference Framework** | PyTorch / ONNX Runtime via Ultralytics Python API |
| **Default Confidence Threshold ($\theta_{conf}$)** | $0.45$ (Balances recall in low light with precision against false gaps) |
| **NMS IoU Threshold ($\theta_{iou}$)** | $0.50$ (Suppresses redundant multi-box overlaps across dense shelf stacks) |
| **Supported Product Categories (Sample Class Set)** | `cereal`, `milk`, `juice`, `chips`, `cookies`, `tea`, `pasta`, `tomato_sauce`, `canned_food` |

### Preprocessing & Normalization Workflow

Before passing captured raw frames to the neural network, the OpenCV pipeline applies the following transformations:
1. **Geometric Validation**: Verifies aspect ratio and rejects frames below $640 \times 480$.
2. **Color Space Normalization**: Converts BGR camera capture to RGB.
3. **Contrast-Limited Adaptive Histogram Equalization (CLAHE)**: Applied on the luminance ($L$) channel in LAB color space to mitigate high-contrast overhead lighting glare across plastic packaging:
   $$\text{CLAHE}(\text{ClipLimit} = 2.0, \text{TileGridSize} = 8 \times 8)$$
4. **Bilinear Rescaling & Padding**: Resizes to $640 \times 640$ preserving aspect ratio with letterbox padding.

### Planogram Deviation & Gap Estimation

The planogram subsystem models the store shelf as a normalized 2D coordinate grid:
$$\text{Bay} = [0.0, 1.0] \times [0.0, 1.0]$$
Divided into discrete compartment bounding boxes:
$$\text{Slot}_{i,j} = [x_{min}, y_{min}, x_{max}, y_{max}]$$

For every detected bounding box $B_k = [x_1, y_1, x_2, y_2]$ with centroid $C_k = \left(\frac{x_1 + x_2}{2}, \frac{y_1 + y_2}{2}\right)$:
* **Compartment Assignment**: $C_k \in \text{Slot}_{i,j}$
* **Class Consistency**: $\text{Class}(B_k) \stackrel{?}{=} \text{ExpectedClass}(\text{Slot}_{i,j})$
* **Gap Index**: If $\sum_{k} \mathbb{I}(C_k \in \text{Slot}_{i,j}) = 0$, the slot is flagged as **Depleted (Stockout)**.

### Clarification on Pitch Deck Benchmark Metric (99.4%)

> [!NOTE]
> **Scientific Integrity & Evaluation Disclaimer:**  
> Slide 1 of the SmartCart AI hackathon presentation deck features the label **"AI DETECT: 99.4%"**.  
> In accordance with software engineering and hackathon evaluation best practices, this metric is documented as an **idealized product target and presentation aspiration**, rather than an independently verified laboratory benchmark.  
> In real-world retail object detection across dense SKU displays with occlusion, standard state-of-the-art vision models typically achieve **88% to 94% mAP@50** on benchmark retail datasets such as SKU-110K or RPC (Retail Product Checkout). Reproducible empirical validation under defined lighting and occlusion conditions remains part of the project's ongoing research roadmap.

---

## Mobile Scan & Go and Verification Workflow

The customer-facing workflow empowers shoppers to scan product barcodes using their smartphone cameras, track cumulative spend in a virtual cart, and complete purchases without traditional cashier checkout lanes.

### Mermaid 3: Scan & Go Secondary Verification

```mermaid
flowchart TD
    %% Shopper Mobile Flow
    C_START(["Customer Starts Mobile Session\n(Open App & Authenticate)"]) --> C_SCAN["Scan Product Barcode\n(EAN-13 / UPC / QR via Camera)"]
    
    C_SCAN --> B_LOOKUP["Lookup Product in Catalog\n(FastAPI: GET /api/v1/products/{barcode})"]
    
    B_LOOKUP --> CART_ADD["Add Scanned Item to Virtual Cart\n(FastAPI: POST /api/v1/cart/items)"]
    
    CART_ADD --> LOG_EVENT["Emit ScanEvent Record\n- session_id\n- product_id\n- timestamp (t_scan)"]
    
    %% Multimodal Evidence Ingestion
    LOG_EVENT --> ENGINE{"Verification Engine\nEvaluation Window:\n|t_scan - t_event| <= tau"}
    
    CV_EVENT["Shelf Camera Event\n(Item count drop at shelf location at t_cv)"] -.-> ENGINE
    WEIGHT_EVENT["Optional Weight Sensor\n(Weight decrease on shelf / increase in cart at t_w)"] -.-> ENGINE

    %% Verification Decisions
    ENGINE --> DECISION{"Evaluate Correlated\nEvidence Matrix"}
    
    DECISION -->|Scan + Vision + Weight Match| VERIFIED["Outcome A: CONSISTENT\n- Evidence compatible with claim\n- Confidence score >= 0.85\n- Cart state flagged VERIFIED"]
    
    DECISION -->|Partial Evidence / Sensor Gap| UNCERTAIN["Outcome B: UNCERTAIN\n- Ambiguous attribution or occluded camera\n- Confidence score 0.50 - 0.84\n- Route to Soft Review / Rescan Prompt"]
    
    DECISION -->|Direct Conflict Detected| MISMATCH["Outcome C: MISMATCH\n- Scan item != Removed item OR\n- Weight mismatch >= 100g OR\n- Shelf removal with NO scan\n- Trigger DISCREPANCY ALERT"]

    %% Checkout Flow
    VERIFIED --> CHECKOUT{"Customer Taps\n'Pay & Finalize'"}
    UNCERTAIN --> RESOLVE{"Staff Soft Check\nor Customer Re-scan"}
    MISMATCH --> AUDIT{"Staff Assistance\nat Exit Kiosk"}

    RESOLVE -->|Confirmed by Staff| CHECKOUT
    AUDIT -->|Discrepancy Corrected| CHECKOUT

    CHECKOUT --> PAYMENT["Execute Server-Side Transaction\n- Deduct inventory\n- Generate Digital Receipt\n- Issue Exit Verification QR"]
    
    PAYMENT --> RECEIPT(["Session Complete\nDigital Receipt Displayed"])

    classDef shopper fill:#e8eaf6,stroke:#3f51b5,stroke-width:1px;
    classDef engine fill:#fff8e1,stroke:#ffa000,stroke-width:1px;
    classDef decision fill:#f3e5f5,stroke:#8e24aa,stroke-width:1px;
    classDef pass fill:#e8f5e9,stroke:#43a047,stroke-width:2px;
    classDef warn fill:#fffde7,stroke:#fbc02d,stroke-width:2px;
    classDef fail fill:#ffebee,stroke:#e53935,stroke-width:2px;

    class C_START,C_SCAN,CART_ADD shopper;
    class B_LOOKUP,LOG_EVENT,PAYMENT,RECEIPT engine;
    class ENGINE,DECISION,CHECKOUT,RESOLVE,AUDIT decision;
    class VERIFIED pass;
    class UNCERTAIN warn;
    class MISMATCH fail;
```

### The Core Philosophy: Scan != Physical Interaction

A central thesis of SmartCart AI is that:
$$\text{Barcode Scan} = \text{Claimed Event} \quad \not\equiv \quad \text{Physical Item Acquisition}$$

1. **The Vulnerability**: In pure Scan & Go systems, a user can scan an item and discard it, or take two items while scanning one, or scan a $1 item while picking up a $20 item.
2. **The Verification Layer**: SmartCart AI introduces **secondary verification**. When a shopper triggers a scan at timestamp $t_{scan}$, the system queries physical telemetry within a temporal window $[t_{scan} - \tau, t_{scan} + \tau]$:
   * Did the shelf camera observing the product's assigned bay observe a removal event?
   * Did the weight sensor register a decrease matching the unit's tare weight?
3. **Attribution Challenge**: In crowded supermarket aisles, multiple shoppers may reach for adjacent items simultaneously. SmartCart AI handles this ambiguity by assigning an **Uncertain** rating rather than an immediate theft accusation, routing the session to a friendly checkout confirmation screen.

---

## Event & Data Flow Sequence

The interaction between client devices, microservices, vision workers, and database transactions follows an asynchronous request-response and event-driven sequence:

### Mermaid 4: Sequence of Telemetry & Verification Flow

```mermaid
sequenceDiagram
    autonumber
    actor Shopper as Customer (Mobile App)
    participant Gateway as FastAPI Gateway
    participant CartSvc as Cart Service
    participant CV as YOLO Vision Pipeline
    participant Correlation as Verification Engine
    participant DB as PostgreSQL DB
    participant WS as WebSocket Broker
    actor Staff as Store Staff (Dashboard)

    %% Session Initialization
    Shopper->>Gateway: POST /api/v1/sessions/start {user_id, cart_id}
    Gateway->>DB: INSERT INTO shopping_sessions (status: ACTIVE)
    DB-->>Gateway: session_id: 1042
    Gateway-->>Shopper: Session Token & Initialized Cart

    %% Periodic Vision Loop (Asynchronous)
    Note over CV,DB: Periodic Shelf Camera Frame Analysis
    CV->>CV: Run YOLO on Bay A3 (Cereal Shelf)
    CV->>DB: Record Shelf State (Count: 3 -> 2 at 12:14:02)
    CV->>Correlation: Notify Shelf Pickup Event (Bay A3, Item: Cereal, 12:14:02)

    %% Customer Barcode Scan
    Shopper->>Gateway: POST /api/v1/cart/scan {session_id: 1042, barcode: "890103001"}
    Gateway->>DB: SELECT * FROM products WHERE barcode = "890103001"
    DB-->>Gateway: Product details (Cereal, $4.99, Weight: 450g)
    Gateway->>CartSvc: Add item to session 1042
    CartSvc->>DB: INSERT INTO cart_items & scan_events (t_scan: 12:14:05)
    CartSvc-->>Gateway: Updated Cart Summary
    Gateway-->>Shopper: Cart Updated: Cereal ($4.99)

    %% Correlation & Verification Engine
    Gateway->>Correlation: Evaluate Scan Event (Session 1042, SKU: Cereal, 12:14:05)
    Correlation->>Correlation: Compare t_scan (12:14:05) with t_cv (12:14:02) [dt = 3s <= tau]
    Correlation->>Correlation: Compare Scanned Class (Cereal) with Vision Class (Cereal)
    Correlation->>DB: INSERT INTO verification_events (status: CONSISTENT, score: 0.95)
    
    %% Alternative: Discrepancy Scenario
    Note over Correlation,Staff: Scenario: Pickup occurred at 12:14:02 but no scan logged after tau=15s
    Correlation->>DB: INSERT INTO restock_alerts / discrepancy_events (UNSCANNED_PICKUP)
    Correlation->>WS: Broadcast Alert {type: "UNSCANNED_PICKUP", aisle: 3, bay: "A3"}
    WS-->>Staff: Real-time Alert on Dashboard (Sound + Toast Notification)

    %% Checkout Finalization
    Shopper->>Gateway: POST /api/v1/checkout/finalize {session_id: 1042}
    Gateway->>Correlation: Request Session Audit Verdict
    Correlation-->>Gateway: Audit Status: VERIFIED (0 Discrepancies)
    Gateway->>DB: BEGIN TRANSACTION
    Gateway->>DB: UPDATE inventory SET quantity = quantity - 1 WHERE sku = 'CEREAL-01'
    Gateway->>DB: UPDATE shopping_sessions SET status = 'COMPLETED'
    Gateway->>DB: INSERT INTO receipts (total: $4.99, transaction_hash)
    Gateway->>DB: COMMIT TRANSACTION
    Gateway-->>Shopper: Digital Receipt & Exit QR Code
```

---

## Feature Inventory & Implementation Status

To ensure absolute transparency and credibility for hackathon judges, all system capabilities are cataloged by their exact implementation maturity:

| Feature | Description | Architecture Layer | Actual Implementation Status |
| :--- | :--- | :--- | :--- |
| **Pretrained YOLO Detection** | Detects retail products from uploaded shelf images using Ultralytics YOLO models | Computer Vision | **Architecture Defined & Prototype Specification** (Model weights & inference scripts specified) |
| **Shelf Occupancy & Counting** | Estimates visible item counts and identifies empty shelf compartments | Computer Vision | **Architecture Defined & Prototype Specification** (Counting and bounding box geometry defined) |
| **Planogram Mapping** | Compares detected bounding box centroids with digital 2D compartment configurations | Computer Vision | **Architecture Defined & Prototype Specification** (Spatial layout schema & comparison logic defined) |
| **Mobile Barcode Scanner** | Scans EAN-13, UPC, and QR barcodes using mobile device camera | Mobile App | **Architecture Defined & Target Integration** (Flutter / mobile scanning library contract specified) |
| **Virtual Shopping Cart** | Adds, increments, decrements, and removes scanned items; calculates totals | Backend API | **Architecture Defined & API Contract Specified** (FastAPI route schemas and session logic) |
| **Sensor Fusion Engine** | Correlates barcode scans with shelf camera detections and weight sensors ($\Delta t \le \tau$) | Processing Engine | **Architecture Defined & Event Matrix Formulated** (Temporal windowing and scoring rules) |
| **Load-Cell Weight Ingestion** | Reads real-time weight shifts on smart shelves or carts | Hardware / IoT | **Simulated** (Hardware target: ESP32; simulated via Python JSON telemetry generator) |
| **Checkout Verification Engine** | Applies rule matrices to classify cart status: *Consistent*, *Uncertain*, *Mismatch* | Application Logic | **Architecture Defined & Rule Engine Formulated** (3 verification scenarios defined) |
| **Restocking Alert Dispatch** | Emits low-stock and stockout alerts when observed shelf counts breach thresholds | Application Logic | **Architecture Defined & Alert Protocol Specified** (WebSocket broadcast & DB alert records) |
| **Store Admin Dashboard** | Web console displaying live shelf inventory, alert feeds, and audit logs | Web Frontend | **Architecture Defined & Target Interface** (Next.js/React layout specified in architecture deck) |
| **Digital Receipt Issuance** | Generates verifiable digital checkout receipts and transactional audit trails | Application Logic | **Architecture Defined & Data Model Specified** (Receipt schema and checkout state transitions) |

---

## Database Schema & Data Model

The persistence layer is modeled in PostgreSQL to provide strict referential integrity, time-series logging, and auditability.

```
       +------------------+         +------------------+
       |     products     |         |      shelves     |
       +------------------+         +------------------+
       | id (PK)          |         | id (PK)          |
       | sku (UQ)         |         | aisle_number     |
       | barcode (UQ)     |         | shelf_level      |
       | name             |         | bay_code         |
       | category         |         +------------------+
       | price            |                   |
       | tare_weight_g    |                   | 1
       +------------------+                   |
          | 1          | 1                    |
          |            |                      | *
          | *          | *          +------------------+
+------------------+ +-----------+  |    planograms    |
|    inventory     | |cart_items |  +------------------+
+------------------+ +-----------+  | id (PK)          |
| id (PK)          | | id (PK)   |  | shelf_id (FK)    |
| product_id (FK)  | | session_id|  | product_id (FK)  |
| total_stock      | | product_id|  | slot_x_start     |
| visible_stock    | | quantity  |  | slot_x_end       |
| safety_threshold | | unit_price|  | expected_facings |
+------------------+ +-----------+  +------------------+
                           |
                           | *
                           | 1
                 +-------------------+
                 | shopping_sessions |
                 +-------------------+
                 | id (PK)           |
                 | user_id           |
                 | cart_id           |
                 | status            |
                 | started_at        |
                 | completed_at      |
                 +-------------------+
                   | 1            | 1
                   |              |
                   | *            | 1
+--------------------+   +--------------------+
|    scan_events     |   |      receipts      |
+--------------------+   +--------------------+
| id (PK)            |   | id (PK)            |
| session_id (FK)    |   | session_id (FK, UQ)|
| product_id (FK)    |   | total_amount       |
| scanned_at         |   | payment_status     |
| client_timestamp   |   | issued_at          |
+--------------------+   +--------------------+
```

### Relational Schema Definitions

```sql
-- Core Product Catalog
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(64) UNIQUE NOT NULL,
    barcode VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    tare_weight_g DECIMAL(8, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Physical Store Shelving Locations
CREATE TABLE shelves (
    id SERIAL PRIMARY KEY,
    aisle_number INT NOT NULL,
    shelf_level INT NOT NULL,
    bay_code VARCHAR(32) NOT NULL,
    camera_id VARCHAR(64)
);

-- Planogram Configuration & Spatial Compartments
CREATE TABLE planograms (
    id SERIAL PRIMARY KEY,
    shelf_id INT REFERENCES shelves(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    compartment_code VARCHAR(32) NOT NULL,
    slot_x_start FLOAT NOT NULL,
    slot_x_end FLOAT NOT NULL,
    expected_facings INT DEFAULT 4,
    min_safety_threshold INT DEFAULT 2
);

-- Live Inventory Ledger
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INT UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    total_store_stock INT NOT NULL DEFAULT 0,
    estimated_visible_stock INT NOT NULL DEFAULT 0,
    last_audited_at TIMESTAMP WITH TIME ZONE
);

-- Customer Shopping Sessions
CREATE TABLE shopping_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    cart_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'ACTIVE', -- ACTIVE, VERIFYING, COMPLETED, FLAGGED
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Scanned Items in Cart
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES shopping_sessions(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- Telemetry & Scan Audit Log
CREATE TABLE scan_events (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES shopping_sessions(id),
    product_id INT REFERENCES products(id),
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    raw_payload JSONB
);

-- Multi-Modal Verification Results
CREATE TABLE verification_events (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES shopping_sessions(id),
    verdict VARCHAR(32) NOT NULL, -- CONSISTENT, UNCERTAIN, MISMATCH
    confidence_score FLOAT NOT NULL,
    evidence_summary JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Store Restock & Discrepancy Alerts
CREATE TABLE restock_alerts (
    id SERIAL PRIMARY KEY,
    shelf_id INT REFERENCES shelves(id),
    product_id INT REFERENCES products(id),
    alert_type VARCHAR(32) NOT NULL, -- LOW_STOCK, STOCKOUT, MISPLACED_ITEM, UNSCANNED_PICKUP
    observed_count INT NOT NULL,
    threshold INT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Immutable Digital Receipts
CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,
    session_id INT UNIQUE REFERENCES shopping_sessions(id),
    total_amount DECIMAL(10, 2) NOT NULL,
    item_count INT NOT NULL,
    payment_status VARCHAR(32) DEFAULT 'SIMULATED_PAID',
    transaction_hash VARCHAR(128) NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## REST & WebSocket API Specification

The FastAPI backend exposes structured endpoints adhering to RESTful conventions with Pydantic validation:

### API Endpoints Summary

| Method | Endpoint | Description | Request Payload | Response Format |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service liveness and dependency status | None | `{"status": "ok", "uptime_s": 1420}` |
| `POST` | `/api/v1/sessions/start` | Initialize shopper Scan & Go cart session | `{"user_id": "u1", "cart_id": "c10"}` | `{"session_id": 1042, "status": "ACTIVE"}` |
| `GET` | `/api/v1/products/{barcode}` | Lookup SKU metadata by scanned barcode | None (URL path parameter) | Product details object |
| `POST` | `/api/v1/cart/scan` | Register product barcode scan in cart | `{"session_id": 1042, "barcode": "..."}` | Updated cart summary |
| `DELETE` | `/api/v1/cart/items/{id}` | Remove scanned item from shopping cart | None (URL path parameter) | Updated cart summary |
| `POST` | `/api/v1/cv/audit-shelf` | Upload shelf image for YOLO detection & audit | Multi-part form: `image`, `shelf_id` | Detection bounding boxes, counts & alerts |
| `POST` | `/api/v1/verify/evaluate` | Evaluate multimodal evidence for session | `{"session_id": 1042}` | Verification verdict, confidence & flags |
| `POST` | `/api/v1/checkout/finalize` | Finalize payment & generate digital receipt | `{"session_id": 1042}` | Digital receipt & transaction hash |
| `GET` | `/api/v1/alerts/active` | Query active low-stock & mismatch alerts | Query params: `shelf_id`, `type` | Array of unresolved alert objects |
| `WS` | `/ws/store-feed` | Duplex WebSocket for real-time alerts | None (Upgrade connection) | Streaming JSON alert messages |

### Sample JSON Payloads

#### 1. Shelf Audit Request & Response
```bash
POST /api/v1/cv/audit-shelf
Content-Type: multipart/form-data
Payload: shelf_id=3, file=@shelf_bay_a1.jpg
```
```json
{
  "shelf_id": 3,
  "bay_code": "BAY-A1",
  "processed_at": "2026-10-19T14:15:22Z",
  "inference_latency_ms": 42.8,
  "summary": {
    "total_detected_objects": 8,
    "unique_classes": 2,
    "occupancy_rate": 0.67
  },
  "compartments": [
    {
      "slot": "A1-1",
      "expected_sku": "CEREAL-WHEAT-01",
      "detected_class": "cereal",
      "detected_count": 2,
      "expected_facings": 4,
      "status": "LOW_STOCK"
    },
    {
      "slot": "A1-2",
      "expected_sku": "CEREAL-CHOC-02",
      "detected_class": "cereal",
      "detected_count": 0,
      "expected_facings": 4,
      "status": "STOCKOUT"
    }
  ],
  "alerts_generated": [
    {
      "type": "STOCKOUT",
      "product": "CEREAL-CHOC-02",
      "message": "Bay A1 Slot 2 is completely depleted."
    }
  ]
}
```

#### 2. Cart Barcode Scan Request & Response
```bash
POST /api/v1/cart/scan
Content-Type: application/json
```
```json
{
  "session_id": 1042,
  "barcode": "8901030018241",
  "client_timestamp": "2026-10-19T14:16:01Z"
}
```
```json
{
  "cart_item_id": 84,
  "product": {
    "sku": "CEREAL-WHEAT-01",
    "name": "Organic Whole Wheat Cereal",
    "price": 4.99,
    "unit": "450g"
  },
  "quantity": 1,
  "cart_summary": {
    "total_items": 3,
    "subtotal": 14.97,
    "estimated_tax": 1.20,
    "estimated_total": 16.17
  },
  "verification_status": "PENDING_CORRELATION"
}
```

#### 3. Real-Time WebSocket Message (Store Associate Alert)
```json
{
  "event_type": "RESTOCK_ALERT",
  "timestamp": "2026-10-19T14:16:05Z",
  "severity": "WARNING",
  "payload": {
    "alert_id": 312,
    "shelf": "Aisle 3, Bay B1",
    "product_name": "Lays Classic Potato Chips",
    "observed_units": 1,
    "threshold": 3,
    "recommended_action": "Replenish 5 units from Backroom Shelf R-04"
  }
}
```

---

## Discrepancy Detection & Verification Logic

SmartCart AI evaluates shopping interactions against three concrete discrepancy scenarios:

```
+--------------------------------------------------------------------------------------------------+
|                               VERIFICATION RULE MATRIX                                           |
+--------------------+-----------------------------+--------------------------------+--------------+
| Scenario           | Evidence Ingested           | Verification Rule              | Action       |
+--------------------+-----------------------------+--------------------------------+--------------+
| 1. Unscanned       | Camera: Item removed        | Shelf count drop observed, but | Emit Alert:  |
|    Pickup          | Scan: No event in window    | NO matching scan within dt<=tau| Staff Audit  |
+--------------------+-----------------------------+--------------------------------+--------------+
| 2. Product         | Camera: Item A removed      | Scanned product category !=    | Emit Alert:  |
|    Mismatch        | Scan: Item B registered     | Visual/planogram product class | Rescan Prompt|
+--------------------+-----------------------------+--------------------------------+--------------+
| 3. Quantity /      | Scale: Delta = -900g        | Weight delta != expected tare  | Emit Alert:  |
|    Weight Mismatch | Scan: 1 item (tare = 450g)  | weight of scanned SKU          | Cart Review  |
+--------------------+-----------------------------+--------------------------------+--------------+
```

### Mathematical Formulation of Correlation

Let $E_{scan}(p, t_s)$ be a barcode scan event for product $p$ at timestamp $t_s$.  
Let $E_{shelf}(p', t_v)$ be a visual shelf-removal observation for class $p'$ at timestamp $t_v$.  
Let $E_{sensor}(\Delta w, t_w)$ be a weight differential reading at timestamp $t_w$.

The temporal correlation window is defined as:
$$|t_s - t_v| \le \tau \quad \text{where } \tau = 15.0 \text{ seconds}$$

The consistency score $S \in [0, 1]$ is computed as:
$$S = w_v \cdot \mathbb{I}(p = p') + w_w \cdot \exp\left(-\frac{|\Delta w - W_p|}{\sigma_w}\right) + w_t \cdot \left(1 - \frac{|t_s - t_v|}{\tau}\right)$$

Where:
* $w_v = 0.50$ (Visual classification weight)
* $w_w = 0.35$ (Sensor weight differential weight)
* $w_t = 0.15$ (Temporal proximity weight)
* $\mathbb{I}(\cdot)$ is the indicator function
* $W_p$ is the catalog tare weight of product $p$

**Verdict Assignment**:
* If $S \ge 0.85 \implies \mathbf{CONSISTENT}$ (Transaction proceeds friction-free).
* If $0.50 \le S < 0.85 \implies \mathbf{UNCERTAIN}$ (Prompts shopper to re-scan or routes to soft staff review).
* If $S < 0.50 \implies \mathbf{MISMATCH}$ (Flags potential discrepancy; logs audit record).

---

## Reproducible Hackathon Demo Scenarios

Judges can evaluate and demonstrate SmartCart AI through 6 structured scenarios defined in the project architecture:

### Scenario 1: Normal Legitimate Purchase
1. Shopper initiates shopping session (`POST /api/v1/sessions/start`).
2. Shelf camera records Cereal facing drop from 4 to 3 units.
3. Shopper scans Cereal barcode within 4 seconds (`POST /api/v1/cart/scan`).
4. Correlation engine computes score $S = 0.94$. Status marked **Consistent**.
5. Checkout completes successfully with digital receipt issuance.

### Scenario 2: Unscanned Item Pickup (Loss Prevention Trigger)
1. Shelf camera registers item removal at Aisle 2, Bay B (Amul Butter).
2. Timer elapses past threshold ($\tau = 15s$) with no barcode scan recorded for that bay.
3. Verification engine emits a `UNSCANNED_PICKUP` alert.
4. WebSocket pushes alert to Store Admin Dashboard showing bay location and timestamp.

### Scenario 3: Product Mismatch (Barcode Swap Prevention)
1. Shopper removes a premium package of Coffee ($14.99).
2. Shopper scans a barcode for instant Noodles ($0.99).
3. Vision engine indicates removed class `beverage_coffee`, while scanned SKU indicates `instant_noodles`.
4. Verification engine flags `PRODUCT_MISMATCH`, generates a warning, and requests shopper rescan.

### Scenario 4: Automated Low-Stock Alert
1. Shelf inspection image uploaded for Bay B1 (Potato Chips).
2. YOLO model detects 1 visible bag (Safety stock threshold = 3).
3. Inventory service updates visible stock count to 1 and flags `LOW_STOCK`.
4. Real-time notification streams to floor staff to pull replenishment units from backroom.

### Scenario 5: Misplaced Product Detection
1. Shelf inspection image uploaded for Bay C2 (Canned Soup shelf).
2. YOLO model detects a box of Tea resting in Slot C2-3.
3. Planogram validator flags compartment conflict: Expected `SOUP-TOMATO`, Observed `TEA-LEMON`.
4. Dashboard updates with `MISPLACED_ITEM` pin for floor associate retrieval.

### Scenario 6: Verified Checkout Finalization
1. Customer reviews virtual cart containing 3 verified items.
2. Shopper taps **Verify & Pay**.
3. Server executes atomic transaction:
   * Re-verifies zero open mismatch flags.
   * Decrements authoritative store inventory.
   * Generates cryptographically hashed digital receipt.
4. Mobile application displays checkout receipt and exit QR code.

---

## Local Setup & Developer Guide

### Prerequisites
* **Python**: Version 3.11, 3.12, or 3.13 installed (`python --version`)
* **Node.js**: Version 18+ or 22+ (for Admin Dashboard)
* **Flutter SDK**: Version 3.24+ (for Mobile Scan & Go application)
* **PostgreSQL**: Version 15+ running locally or in Docker

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/YourUsername/SmartCart-AI.git
cd SmartCart-AI
```

#### 2. Configure Backend Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install core dependencies
pip install fastapi uvicorn pydantic opencv-python pillow websockets python-dotenv
```

#### 3. Database Initialization
```bash
# Ensure PostgreSQL is running and database exists
# CREATE DATABASE smartcart_db;

# Run migrations (when Alembic configured) or initialize schema:
# python scripts/init_db.py
```

#### 4. Run the Backend API Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Once started, visit the interactive Swagger API documentation:
* **Interactive Docs**: `http://localhost:8000/docs`
* **Alternative ReDoc**: `http://localhost:8000/redoc`

#### 5. Run the Simulated Telemetry Generator
```bash
python scripts/simulate_events.py --scenario normal_purchase
```

---

## Environment Configuration

Create a `.env` file in the project root based on the following template:

```ini
# ==============================================================================
# SmartCart AI - Application Environment Configuration
# ==============================================================================

# Application Gateway
APP_ENV=development
APP_PORT=8000
DEBUG=True
SECRET_KEY=change-this-to-a-secure-random-secret-in-production

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartcart_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Computer Vision & Inference Engine
YOLO_MODEL_PATH=cv_pipeline/weights/yolov8n.pt
INFERENCE_CONFIDENCE_THRESHOLD=0.45
IOU_THRESHOLD=0.50
CLAHE_CLIP_LIMIT=2.0

# Verification & Correlation Parameters
CORRELATION_WINDOW_SECONDS=15.0
WEIGHT_TOLERANCE_GRAMS=50.0
MIN_VERIFICATION_CONFIDENCE=0.85

# WebSocket & Streaming Configuration
WS_HEARTBEAT_INTERVAL_SECONDS=30

# CORS Allowed Origins
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## Visual Assets & Interface Mockups

The project architecture incorporates intuitive interfaces designed for high-throughput retail operations:

### Planned UI & Workflow Assets

| Interface Screen | Description | Architectural Source |
| :--- | :--- | :--- |
| **Mobile Scanner Screen** | Camera view with bounding crosshairs, rapid barcode reader, and haptic feedback | Presentation Slide 6 (Mobile Journey) |
| **Virtual Shopping Cart** | Live summary of scanned products, tare weights, running total, and checkout verification button | Presentation Slide 6 & 11 |
| **AI Shelf Detection Overlay** | Annotated shelf image showing bounding boxes, classes (Cereal, Milk, Chips), and compartment counts | Presentation Slide 5 (AI Auditing) |
| **Store Inventory Dashboard** | Real-time metric cards (Total Products, Low Stock Alerts, Stockout Events, Misplaced Items) | Presentation Slide 8 & 9 (Replenishment) |
| **Discrepancy Resolution Modal**| Staff triage view displaying split evidence (Camera timestamp vs. Cart scan log) | Presentation Slide 7 & 8 |

> [!TIP]
> Genuine visual diagrams extracted directly from the hackathon submission deck are referenced in the [High-Level System Architecture](#high-level-system-architecture) and [Reproducible Hackathon Demo Scenarios](#reproducible-hackathon-demo-scenarios) sections.

---

## Testing, Security & Reliability

### Engineering Controls

1. **Server-Side Transaction Authority**:
   The mobile client is strictly treated as an untrusted presentation layer. All item prices, cart sums, tax calculations, and stock deductions are calculated on the FastAPI server using authoritative database records.
2. **Idempotent Scan Processing**:
   Every barcode scan includes a client-generated UUID `idempotency_key` preventing network retransmissions from accidentally double-charging items.
3. **Audit Trail Logging**:
   Every verification decision, whether *Consistent*, *Uncertain*, or *Mismatch*, is permanently persisted in the `verification_events` ledger for retrospective review and loss-prevention analysis.
4. **Input Validation**:
   All incoming REST payloads are validated using strict Pydantic schemas, rejecting malformed coordinates, negative quantities, or invalid barcode character encodings.

---

## Current Limitations & Future Roadmap

### Current Limitations
* **Attribution in High-Density Footfall**: When 3+ shoppers reach into the same shelf bay simultaneously, associating an item removal with a specific shopper's mobile session remains challenging without multi-camera shopper tracking.
* **Packaging Variation**: Pretrained generic object detection models require domain-specific fine-tuning on high-resolution retail packaging datasets (e.g., SKU-110K) to reliably separate subtle brand sub-variants.
* **Hardware Integration**: The load-cell weight telemetry is currently demonstrated using simulated event streams; physical ESP32 load-cells are specified as prototype hardware targets.
* **Exit Gate Automation**: Physical automated turnstile exit gates are not included in this prototype; verification currently issues a verifiable digital receipt and QR code.

### Future Roadmap
- [ ] **Multi-Camera Shopper Re-Identification (Re-ID)**: Track shopper trajectories from entrance to exit to maintain persistent session-to-person association across aisle transitions.
- [ ] **Edge AI Acceleration**: Compile YOLO models with TensorRT / OpenVINO for sub-15ms inference directly on NVIDIA Jetson or on-camera edge devices.
- [ ] **Real IoT Smart Shelves**: Fabricate physical shelf prototypes with integrated HX711 load-cell amplifiers and ESP32 microcontrollers streaming weight shifts over MQTT.
- [ ] **Payment Gateway Integration**: Connect checkout finalization to Stripe / UPI gateways for automated card/wallet transactions.
- [ ] **Multi-Store Enterprise Sync**: Centralized multi-tenant inventory management across distributed supermarket chains.

---

## Team LIFTOFF & Institutional Affiliation

SmartCart AI is developed by **Team LIFTOFF** representing **Universal SkillTech University (USTU)** for the **Computer Vision AI Hackathon 2026**:

* **Ashraf Hussain Siddiqui** — Team Leader (`siddiqui.hussain@ustu.edu.in`)
* **Krishna Prajapati** — Team Member (AIML)
* **Goldi Varma** — Team Member (CSE)
* **Tejasvi N Ojha** — Team Member (CSE)
* **Sanika Rajendra Jadhav** — Team Member (CSE)
* **Nisha Kushwaha** — Team Member (CSE)

**Institution Details:**  
Universal SkillTech University (USTU)  
Approved by AICTE / UGC  
Institutional Endorsement: Dr. Jitendra B. Patil (Principal / Vice Chancellor)

---

## License & Acknowledgements

### License
This project is released under the [MIT License](LICENSE) — see the LICENSE file for details.

### Acknowledgements
* **E-Cell IIT Bombay & Everseen**: For organizing the Computer Vision AI Hackathon 2026 and sponsoring Problem Statement 2 (Mobile Scan & Go – Checkout Anywhere Loss Prevention).
* **Ultralytics**: For the open-source YOLO object detection architecture.
* **FastAPI & Flutter Communities**: For high-performance backend and mobile application frameworks.
* **Universal SkillTech University**: For academic guidance, computational resources, and project mentorship.

---

<div align="center">
  <sub>SmartCart AI • Team LIFTOFF • Computer Vision AI Hackathon 2026</sub><br>
  <b>Shop Smarter. Verify Instantly. Restock Proactively.</b>
</div>
