# Sequencer Orchestrator

A CAR-T cell therapy orchestration engine that manages the full vein-to-vein patient journey from HCP enrollment through infusion.

## What This Is

CAR-T cell therapy requires extracting a patient's T-cells (apheresis), engineering them at a manufacturing site, releasing them through QC, shipping them under strict cold-chain conditions, and infusing them back into the patient — a process spanning weeks and dozens of handoffs across institutions. This system orchestrates every stage of that journey, enforcing state machine transitions, emitting auditable events, and ensuring no step is skipped or duplicated. GXP compliance mandates a tamper-evident audit trail at every stage, which this system provides through immutable event records and idempotency guarantees.

## Architecture

- **Spring Boot 3.5 (Java 21)** — backend orchestration engine
- **Angular 19** — real-time polling dashboard (Angular Material, Signals)
- **PostgreSQL 15** — primary datastore with Flyway schema management
- **Redis 7** — idempotency and caching (configured, Phase 2+)
- **AWS SQS/SNS via LocalStack** — event fan-out and messaging (Phase 2+)
- **Apache Kafka** — event streaming and replay (Phase 3+)

## Patient Journey (19 Statuses)

```
ENROLLED → SLOT_REQUESTED → APHERESIS_SCHEDULED → APHERESIS_COMPLETE
→ IN_TRANSIT_INBOUND → ACCESSIONED → MANUFACTURING → QC_IN_PROGRESS
→ RELEASED → IN_TRANSIT_OUTBOUND → RECEIVED_AT_CENTER → LYMPHODEPLETION
→ INFUSION_READY → INFUSED → MONITORING → CLOSED
```

Terminal states: `CLOSED`, `FAILED`, `CANCELLED`

## Build Phases

- **Phase 1: Naive polling orchestrator** — deliberately built with a polling loop to expose failure modes: missed events, duplicate processing, thundering herd, no idempotency
- **Phase 2: SQS/SNS event-driven** — outbox pattern eliminates dual-write; saga orchestrator manages compensating transactions; idempotency keys prevent duplicate processing
- **Phase 3: Kafka consumer group** — events partitioned by patient ID ensure ordered processing per patient; consumer groups enable replay and parallel scaling
- **Phase 4: AWS Lambda** — vendor notification layer handles inbound webhooks from external sites with partial batch failure handling to avoid message loss
- **Phase 5: Angular dashboard** — Kanban board visualizes patient pipeline by stage; SSE delivers live updates without polling; system health panel surfaces consumer lag and dead-letter queue depth

## Prerequisites

- Java 21
- Maven 3.9+
- Docker and Docker Compose
- Node.js 18+

## Running Locally

### 1. Start infrastructure

```bash
docker-compose up -d
```

### 2. Run the backend

```bash
./mvnw spring-boot:run
```

Flyway will automatically apply all migrations on first startup.

### 3. Run the frontend

```bash
cd frontend
npm install
npm start
```

The Angular dev server proxies `/api` to `localhost:8080`, so CORS is not needed locally.

### 4. Run a second backend instance (for race condition testing)

```bash
java -jar target/sequencer-orchestrator-*.jar --server.port=8081
```

Both instances will poll the same database concurrently, exposing the locking gap described in Observations below.

### 5. Verify

- Frontend: http://localhost:4200
- API: http://localhost:8080
- PostgreSQL: `localhost:5432` / DB: `sequencer-orchestrator`
- Redis: `localhost:6379`

## Database

Flyway manages all schema migrations. Never use `ddl-auto=create` or `ddl-auto=update` — all schema changes go through versioned migration scripts.

Migrations live in `src/main/resources/db/migration/`.

| Migration | Description |
|-----------|-------------|
| V1 | `patients` table |
| V2 | `therapy_orders` table |
| V7 | `outbox_events` table (JSONB payload) |
| V8 | `processed_events` table (idempotency) |
| V9 | `order_status_history` table |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/patients` | Enroll a new patient |
| `POST` | `/api/orders` | Create a therapy order for a patient |
| `GET` | `/api/orders` | List all orders (optional `?status=` filter) |
| `GET` | `/api/orders/{id}` | Get full order detail by ID |
| `GET` | `/api/orders/{id}/history` | Get full status transition history for an order |

### Sample — Enroll a patient

```json
POST /api/patients
{
  "name": "Alex",
  "dateOfBirth": "1998-05-30",
  "diagnosisCode": "C91.1",
  "hcpID": "550e8400-e29b-41d4-a716-446655440000",
  "treatmentCenterID": "7f3b2c1a-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

### Sample — Create an order

```json
POST /api/orders
{
  "patientId": "<patient-uuid>",
  "hcpID": "550e8400-e29b-41d4-a716-446655440000",
  "treatmentCenterID": "7f3b2c1a-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

## Polling Orchestrator

A background job (`@Scheduled(fixedDelay = 5000)`) runs every 5 seconds and advances all active therapy orders through the clinical state machine. Terminal states (`CLOSED`, `FAILED`, `CANCELLED`) are excluded. Each transition is logged with the order ID, from-status, and to-status. Exceptions per order are caught and logged — one failing order does not block others.

Every transition (including the initial `ENROLLED` written on order creation) is recorded in `order_status_history`.

## Angular Dashboard

The dashboard polls `GET /api/orders` every 5 seconds using RxJS `interval` + `switchMap`. It uses Angular 19 standalone components with Angular Material and Signals.

**Features:**
- Live order table: order ID, patient name, status (colour-coded), days since creation, last updated
- Active order count via `computed()` signal (excludes `CLOSED`, `FAILED`, `CANCELLED`)
- Click any row to open a **Material Dialog** showing the full status transition history for that order — from-status, to-status, and timestamp for every step
- Automatic cleanup of polling subscriptions on component destroy

**Key files:**

| File | Purpose |
|------|---------|
| `frontend/src/app/features/dashboard/dashboard.ts` | Main component — polling, signals, row click → dialog |
| `frontend/src/app/features/dashboard/order-history-dialog.ts` | Standalone dialog component for status history |
| `frontend/src/app/services/order.service.ts` | `getOrders()`, `getStatusHistory(orderId)` |
| `frontend/src/app/interfaces/Order.ts` | Order response shape |
| `frontend/src/app/interfaces/OrderStatusHistory.ts` | History entry shape |
| `frontend/src/app/enum/OrderStatus.ts` | 19 status values mirroring the backend enum |
| `frontend/proxy.conf.json` | Dev proxy: `/api` → `localhost:8080` |

## Observations — Phase 1 Failure Modes

These are intentional gaps in the Phase 1 design, studied by running the system under realistic conditions before applying fixes in Phase 2+.

### Observation 1 — Race Condition (No Locking) ✓ Observed

**What it exposes:** The poller has no locking. If two instances run simultaneously, both can read the same order within the same 5-second tick and advance it twice.

**How to trigger:**
1. Run a primary instance on port 8080 (`./mvnw spring-boot:run`)
2. Build the JAR and run a second instance on port 8081 (`java -jar target/*.jar --server.port=8081`)
3. Create a few orders via the API
4. Watch the `order_status_history` table — both pollers will write history entries for the same order within the same tick

**What to look for:**
- Orders that skip a status (e.g. jump from `ENROLLED` directly to `APHERESIS_SCHEDULED`)
- Two history rows for the same order with `changed_at` values milliseconds apart
- `updated_at` on the order changing twice within a single 5-second window

**Confirmed on order `a2f5c114-84ec-4a6c-895f-33f303a28e57`:** consecutive status transitions appeared within 2–3 seconds — well under the 5-second polling interval — confirming both instances picked up the same order in the same tick and each wrote a history entry independently.

**Root cause:** No `SELECT ... FOR UPDATE` or `@Version` optimistic lock. Both instances read the same row, both call `advanceTo()`, and both `save()` — last write wins on the order row, but both writes land in the history table, making the double-advance visible.

**Fix (Phase 2):** Pessimistic row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`) or `@Version`-based optimistic locking with retry.

---

### Observation 2 — Status History Gap (Now Fixed in Phase 1.6)

**What it exposed:** Before V9, `therapy_orders` only stored the current status. If a race condition advanced an order twice, there was no record of the skipped state — only the final status and the last `updated_at` were visible, making the race condition invisible after the fact.

**Fix applied:** `order_status_history` table (V9 migration). Every transition — including the initial `ENROLLED` on order creation — is written as an immutable row with `from_status`, `to_status`, and `changed_at`. The race condition in Observation 1 now leaves a visible fingerprint: two rows for the same order with timestamps milliseconds apart. The history is surfaced in the dashboard via a Material Dialog on row click.

---

### Observation 3 — Thundering Herd

**What it exposes:** Both instances query `findByStatusNotIn(CANCELLED, CLOSED, FAILED)` with no pagination — every poll loads every active order into memory. As order volume grows, each tick becomes a full table scan, and two instances double that load.

**Fix (Phase 2):** Outbox pattern + SQS. Orders are pushed into a queue on state change; each consumer only processes what's assigned to it.

---

### Observation 4 — No Idempotency Guard

**What it exposes:** If the poller crashes mid-tick after saving the order but before completing, the same transition can be retried without detection. The `processed_events` table exists but is not wired into the polling path.

**Fix (Phase 2):** Idempotency keys (stored in `processed_events`) checked before processing each event; the outbox guarantees at-least-once delivery and the idempotency key collapses duplicates to exactly-once.

## Build Status

| Phase | Step | Status |
|-------|------|--------|
| Phase 1 | 1.1 — Database schema (Flyway V1, V2, V7, V8) | Complete |
| Phase 1 | 1.2 — JPA entities and repositories | Complete |
| Phase 1 | 1.3 — REST API (patients, orders) | Complete |
| Phase 1 | 1.4 — Polling orchestrator | Complete |
| Phase 1 | 1.5 — Angular polling dashboard | Complete |
| Phase 1 | 1.6 — Status history (V9 migration, entity, endpoint, dialog) | Complete |
| Phase 2 | SQS/SNS event-driven + locking + idempotency | Pending |
| Phase 3 | Kafka consumer group | Pending |
| Phase 4 | AWS Lambda vendor layer | Pending |
| Phase 5 | Angular complete dashboard (SSE, Kanban) | Pending |

## Project Structure

```
src/main/java/com/sequencer/orchestrator/
├── domain/
│   ├── model/
│   │   ├── base/        — BaseEntity, AuditableEntity
│   │   ├── entity/      — Patient, TherapyOrder, OutboxEvent, ProcessedEvent, OrderStatusHistory
│   │   └── enums/       — OrderStatus, PatientStatus, EventType, AggregateType
│   └── repository/      — Spring Data JPA repositories
├── api/
│   ├── controller/      — OrderController, PatientController
│   ├── dto/             — Request/response DTOs (incl. OrderStatusHistoryResponse)
│   └── exception/       — GlobalExceptionHandler
└── service/             — OrderService, PatientService, OrderPollingOrchestrator

src/main/resources/db/migration/
├── V1__create_patients.sql
├── V2__create_therapy_orders.sql
├── V7__create_outbox_events.sql
├── V8__create_processed_events.sql
└── V9__create_order_status_history.sql

frontend/src/app/
├── features/dashboard/
│   ├── dashboard.ts              — main component
│   ├── dashboard.html            — Material table + row click
│   ├── dashboard.css
│   └── order-history-dialog.ts  — history popup dialog
├── services/order.service.ts
├── interfaces/
│   ├── Order.ts
│   └── OrderStatusHistory.ts
└── enum/OrderStatus.ts
```
