# Sequencer Orchestrator

A CAR-T cell therapy orchestration engine that manages the full vein-to-vein patient journey from HCP enrollment through infusion.

## What This Is

CAR-T cell therapy requires extracting a patient's T-cells (apheresis), engineering them at a manufacturing site, releasing them through QC, shipping them under strict cold-chain conditions, and infusing them back into the patient — a process spanning weeks and dozens of handoffs across institutions. This system orchestrates every stage of that journey, enforcing state machine transitions, emitting auditable events, and ensuring no step is skipped or duplicated. GXP compliance mandates a tamper-evident audit trail at every stage, which this system provides through immutable event records and idempotency guarantees.

## Architecture

- **Spring Boot 3.2 (Java 21)** — backend orchestration engine
- **Angular 17** — real-time dashboard
- **PostgreSQL 15** — primary datastore with Flyway schema management
- **Redis 7** — idempotency and caching
- **AWS SQS/SNS via LocalStack** — event fan-out and messaging
- **Apache Kafka** — event streaming and replay

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
- Node.js 18+ (for frontend, Phase 5 only)

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

### 3. Verify

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
│   ├── controller/      — REST controllers
│   └── dto/             — Request and response DTOs
└── service/             — Business logic
```
