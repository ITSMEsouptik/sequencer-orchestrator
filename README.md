# Sequencer Orchestrator

A CAR-T cell therapy orchestration engine that manages the full vein-to-vein patient journey from HCP enrollment through infusion.

## What This Is

CAR-T cell therapy requires extracting a patient's T-cells (apheresis), engineering them at a manufacturing site, releasing them through QC, shipping them under strict cold-chain conditions, and infusing them back into the patient — a process spanning weeks and dozens of handoffs across institutions. This system orchestrates every stage of that journey, enforcing state machine transitions, emitting auditable events, and ensuring no step is skipped or duplicated. GXP compliance mandates a tamper-evident audit trail at every stage, which this system provides through immutable event records and idempotency guarantees.

## Architecture

- **Spring Boot 3.5 (Java 21)** — backend orchestration engine
- **Angular 17** — real-time polling dashboard (Angular Material, Signals)
- **PostgreSQL 15** — primary datastore with Flyway schema management
- **Redis 7** — idempotency and caching (configured, Phase 2+)
- **AWS SQS/SNS via LocalStack** — event fan-out and messaging (Phase 2+)
- **Apache Kafka** — event streaming and replay (Phase 3+)

## Patient Journey (11 Stages)

1. **HCP Enrollment** — healthcare provider and site are credentialed and registered
2. **Patient Registration** — patient identity and insurance are verified and entered
3. **Apheresis Scheduling** — leukapheresis appointment is scheduled at a certified collection site
4. **Cell Collection** — T-cells are collected and the apheresis bag is assigned a chain-of-custody ID
5. **Manufacturing Release** — the collection is shipped to the manufacturing site and accepted
6. **Manufacturing in Progress** — T-cells are engineered and expanded under GMP conditions
7. **QC Testing** — product undergoes potency, sterility, and identity release testing
8. **Product Release** — QC passes and the lot is released for patient use
9. **Cold-Chain Shipping** — cryopreserved product ships to the infusion site with temperature monitoring
10. **Infusion Scheduling** — infusion slot is confirmed at the treating institution
11. **Post-Infusion Monitoring** — patient is monitored for CRS/ICANS and long-term response

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

Wait for all services to be healthy:

```bash
docker-compose ps
```

### 2. Run the backend

```bash
mvn spring-boot:run
```

Flyway will automatically apply all migrations on first startup.

### 3. Run the frontend

```bash
cd frontend
npm install
npm start
```

The Angular dev server proxies `/api` to `localhost:8080`, so CORS is not needed locally.

### 4. Verify

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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/patients` | Enroll a new patient |
| `POST` | `/api/orders` | Create a therapy order for a patient |
| `GET` | `/api/orders` | List all orders (optional `?status=` filter) |
| `GET` | `/api/orders/{id}` | Get full order detail by ID |

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

A background job runs every 5 seconds and advances all active therapy orders through the clinical state machine:

```
ENROLLED → SLOT_REQUESTED → APHERESIS_SCHEDULED → APHERESIS_COMPLETE
→ IN_TRANSIT_INBOUND → ACCESSIONED → MANUFACTURING → QC_IN_PROGRESS
→ RELEASED → IN_TRANSIT_OUTBOUND → RECEIVED_AT_CENTER → LYMPHODEPLETION
→ INFUSION_READY → INFUSED → MONITORING → CLOSED
```

Terminal states (`CLOSED`, `FAILED`, `CANCELLED`) are excluded from polling. Each transition is logged with the order ID, from status, and to status. Exceptions per order are caught and logged — one failing order does not block others.

## Angular Dashboard

The dashboard polls `GET /api/orders` every 5 seconds using RxJS `interval` + `switchMap`. It uses Angular 17 standalone components with Angular Material and Signals.

**Features:**
- Live order table: order ID, patient name, status chip, days since creation, last updated
- Active order count via `computed()` signal (excludes `CLOSED`, `FAILED`, `CANCELLED`)
- Automatic cleanup of subscriptions on component destroy

**Key files:**

| File | Purpose |
|------|---------|
| `frontend/src/app/features/dashboard/dashboard.ts` | Main component — polling, signals, Material table |
| `frontend/src/app/services/order.service.ts` | `getOrders(status?)` → `Observable<Order[]>` |
| `frontend/src/app/interfaces/Order.ts` | Order response shape |
| `frontend/src/app/enum/OrderStatus.ts` | 19 status values mirroring the backend enum |
| `frontend/proxy.conf.json` | Dev proxy: `/api` → `localhost:8080` |

## Build Status

| Phase | Step | Status |
|-------|------|--------|
| Phase 1 | 1.1 — Database schema (Flyway migrations) | Complete |
| Phase 1 | 1.2 — JPA entities and repositories | Complete |
| Phase 1 | 1.3 — REST API | Complete |
| Phase 1 | 1.4 — Polling orchestrator | Complete |
| Phase 1 | 1.5 — Angular polling dashboard | Complete |
| Phase 2 | SQS/SNS event-driven | Pending |
| Phase 3 | Kafka consumer group | Pending |
| Phase 4 | AWS Lambda vendor layer | Pending |
| Phase 5 | Angular complete dashboard (SSE, Kanban) | Pending |

## Project Structure

```
src/main/java/com/sequencer/orchestrator/
├── domain/
│   ├── model/
│   │   ├── base/        — BaseEntity, AuditableEntity
│   │   ├── entity/      — Patient, TherapyOrder, OutboxEvent, ProcessedEvent
│   │   └── enums/       — OrderStatus, PatientStatus, EventType, AggregateType
│   └── repository/      — Spring Data JPA repositories
├── api/
│   ├── controller/      — REST controllers (PatientController, OrderController)
│   ├── dto/             — Request and response DTOs
│   └── exception/       — GlobalExceptionHandler
└── service/             — Business logic + polling orchestrator
```
