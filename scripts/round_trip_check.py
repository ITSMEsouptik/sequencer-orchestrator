#!/usr/bin/env python3
"""
Round-trip health check for the Sequencer-Orchestrator POC.

Starts all four vendor consumers as subprocesses, creates a patient + order
via the REST API, then polls the order status every 2 s watching the saga
advance through all states to CLOSED. Prints a timestamped transition log
and a final PASS / FAIL with the stall point if it times out.

Usage:
    pip install requests boto3
    python scripts/round_trip_check.py

Prerequisites:
    - docker-compose up -d          (LocalStack + Postgres + Redis)
    - Spring Boot orchestrator running on localhost:8080
    - LocalStack queues initialised  (create-queues.sh must have run)
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

# ── config ───────────────────────────────────────────────────────────────────

ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8080")
LOCALSTACK_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:000000000000:sequencer-orchestrator-events"
)
TIMEOUT_SECONDS = int(os.environ.get("ROUND_TRIP_TIMEOUT", "120"))
POLL_INTERVAL = 2

# Expected state sequence (excluding terminal states)
EXPECTED_SEQUENCE = [
    "SLOT_REQUESTED",
    "APHERESIS_SCHEDULED",
    "IN_TRANSIT_INBOUND",
    "MANUFACTURING",
    "QC_IN_PROGRESS",
    "RELEASED",
    "IN_TRANSIT_OUTBOUND",
    "RECEIVED_AT_CENTER",
    "INFUSED",
    "MONITORING",
    "CLOSED",
]

VENDOR_CONFIGS = [
    {
        "VENDOR_ID":            "manufacturing",
        "QUEUE_URL":            f"{LOCALSTACK_ENDPOINT}/000000000000/sequencer-manufacturing-inbound",
        "STEP_COMPLETION_MAP":  "MANUFACTURING_SLOT_REQUESTED:MANUFACTURING_SLOT_CONFIRMED,MANUFACTURING_STARTED:MANUFACTURING_CRYOPRESERVATION_COMPLETE",
        "WORK_DELAY_SECONDS":   "1",
    },
    {
        "VENDOR_ID":            "logistics",
        "QUEUE_URL":            f"{LOCALSTACK_ENDPOINT}/000000000000/sequencer-logistics-inbound",
        "STEP_COMPLETION_MAP":  "INBOUND_SHIPMENT_DISPATCHED:PRODUCT_ACCESSIONED,OUTBOUND_SHIPMENT_DISPATCHED:OUTBOUND_SHIPMENT_RECEIVED",
        "WORK_DELAY_SECONDS":   "1",
    },
    {
        "VENDOR_ID":                 "clinical",
        "QUEUE_URL":                 f"{LOCALSTACK_ENDPOINT}/000000000000/sequencer-clinical-inbound",
        "STEP_COMPLETION_MAP":       "APHERESIS_SCHEDULED:APHERESIS_COMPLETE,INFUSION_SCHEDULED:INFUSION_COMPLETE",
        "WORK_DELAY_SECONDS":        "1",
        "MONITORING_CLOSE_DELAY_SECONDS": "5",
    },
    {
        "VENDOR_ID":            "qc-lab",
        "QUEUE_URL":            f"{LOCALSTACK_ENDPOINT}/000000000000/sequencer-qc-lab-inbound",
        "STEP_COMPLETION_MAP":  "QC_INITIATED:QC_PASSED",
        "WORK_DELAY_SECONDS":   "1",
    },
]

COMMON_ENV = {
    "SNS_TOPIC_ARN":         TOPIC_ARN,
    "AWS_REGION":             "us-east-1",
    "AWS_ENDPOINT_URL":       LOCALSTACK_ENDPOINT,
    "AWS_ACCESS_KEY_ID":      "test",
    "AWS_SECRET_ACCESS_KEY":  "test",
    "IDEMPOTENCY_DB_PATH":    "",  # filled per-vendor below
}

# ── helpers ───────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def ok(msg: str) -> None:
    print(f"  [{ts()}] ✓ {msg}")


def fail(msg: str) -> None:
    print(f"  [{ts()}] ✗ {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"  [{ts()}] ! {msg}")


def check_prerequisites() -> None:
    print("\n── Prerequisites ────────────────────────────────────────")
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/api/orders", timeout=5)
        r.raise_for_status()
        ok(f"Orchestrator reachable at {ORCHESTRATOR_URL}")
    except Exception as exc:
        fail(f"Orchestrator not reachable: {exc}\n  → Start with: ./mvnw spring-boot:run")

    import boto3
    try:
        sqs = boto3.client(
            "sqs", region_name="us-east-1", endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test", aws_secret_access_key="test",
        )
        queues = sqs.list_queues(QueueNamePrefix="sequencer").get("QueueUrls", [])
        if not queues:
            fail("No sequencer queues found in LocalStack.\n  → docker-compose up -d and wait for create-queues.sh")
        ok(f"LocalStack has {len(queues)} sequencer queue(s)")
        for q in queues:
            print(f"       {q.split('/')[-1]}")
    except Exception as exc:
        fail(f"LocalStack not reachable: {exc}\n  → docker-compose up -d")


def enroll_patient() -> str:
    unique = uuid.uuid4().hex[:6].upper()
    payload = {
        "name":             f"Test Patient {unique}",
        "dateOfBirth":      "1985-03-15",
        "diagnosisCode":    "C91.0",
        "hcpID":            str(uuid.uuid4()),
        "treatmentCenterID": str(uuid.uuid4()),
    }
    r = requests.post(f"{ORCHESTRATOR_URL}/api/patients", json=payload, timeout=10)
    if r.status_code not in (200, 201):
        fail(f"Patient enroll failed {r.status_code}: {r.text}")
    patient_id = r.json()["id"]
    ok(f"Patient enrolled id={patient_id} name={payload['name']}")
    return patient_id


def create_order(patient_id: str) -> str:
    payload = {
        "patientId":        patient_id,
        "hcpID":            str(uuid.uuid4()),
        "treatmentCenterID": str(uuid.uuid4()),
    }
    r = requests.post(f"{ORCHESTRATOR_URL}/api/orders", json=payload, timeout=10)
    if r.status_code not in (200, 201):
        fail(f"Order create failed {r.status_code}: {r.text}")
    order_id = r.json()["orderId"]
    ok(f"Order created id={order_id} status=SLOT_REQUESTED")
    return order_id


def start_vendor_consumers() -> list:
    consumer_script = Path(__file__).parent.parent / "vendor-consumer" / "main.py"
    if not consumer_script.exists():
        fail(f"Vendor consumer not found at {consumer_script}")

    procs = []
    for cfg in VENDOR_CONFIGS:
        env = {**os.environ, **COMMON_ENV, **cfg}
        env["IDEMPOTENCY_DB_PATH"] = f"/tmp/vendor-{cfg['VENDOR_ID']}-idempotency.db"
        proc = subprocess.Popen(
            [sys.executable, str(consumer_script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append((cfg["VENDOR_ID"], proc))
        ok(f"Vendor consumer started: {cfg['VENDOR_ID']} (pid={proc.pid})")
    return procs


def poll_until_closed(order_id: str) -> None:
    print(f"\n── Watching saga advance (timeout={TIMEOUT_SECONDS}s) ──────────────")
    deadline = time.time() + TIMEOUT_SECONDS
    last_status = None
    seen = []

    while time.time() < deadline:
        try:
            r = requests.get(f"{ORCHESTRATOR_URL}/api/orders/{order_id}", timeout=5)
            r.raise_for_status()
            status = r.json()["status"]
        except Exception as exc:
            warn(f"Poll error: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        if status != last_status:
            elapsed = int(TIMEOUT_SECONDS - (deadline - time.time()))
            print(f"  [{ts()}] → {status}  (+{elapsed}s)")
            seen.append(status)
            last_status = status

        if status == "CLOSED":
            return
        if status == "FAILED":
            fail(f"Saga reached FAILED — check orchestrator logs for ORDER_FAILED event")
        if status == "CANCELLED":
            fail("Saga reached CANCELLED")

        time.sleep(POLL_INTERVAL)

    # Timed out — report stall point
    expected_remaining = [s for s in EXPECTED_SEQUENCE if s not in seen]
    stall_at = expected_remaining[0] if expected_remaining else "unknown"
    print(f"\n  [{ts()}] Stall analysis:")
    print(f"    Last observed status : {last_status}")
    print(f"    Expected next status : {stall_at}")
    _diagnose_stall(last_status)
    fail(f"Timed out after {TIMEOUT_SECONDS}s — saga stalled at {last_status}")


def _diagnose_stall(status: str) -> None:
    """Print a likely cause based on which vendor step should have fired."""
    hints = {
        "SLOT_REQUESTED":    "manufacturing queue never received MANUFACTURING_SLOT_REQUESTED — check SNS publish attribute or LocalStack topic subscription",
        "APHERESIS_SCHEDULED": "clinical queue never received APHERESIS_SCHEDULED — check filter policy or SlotConfirmedHandler emit",
        "IN_TRANSIT_INBOUND":  "logistics queue never received INBOUND_SHIPMENT_DISPATCHED",
        "ACCESSIONED":         "manufacturing queue never received MANUFACTURING_STARTED",
        "MANUFACTURING":       "manufacturing consumer did not send MANUFACTURING_CRYOPRESERVATION_COMPLETE",
        "QC_IN_PROGRESS":      "qc-lab queue never received QC_INITIATED",
        "RELEASED":            "PRODUCT_RELEASED self-echo not handled — check ReleaseHandler",
        "IN_TRANSIT_OUTBOUND": "logistics queue never received OUTBOUND_SHIPMENT_DISPATCHED",
        "RECEIVED_AT_CENTER":  "clinical queue never received INFUSION_SCHEDULED — check OutboundShipmentReceivedHandler",
        "INFUSED":             "clinical consumer did not send CASE_CLOSED after INFUSION_COMPLETE",
        "MONITORING":          "MonitoringHandler not reached — CASE_CLOSED not published",
    }
    hint = hints.get(status, "check orchestrator logs for the handler that should fire next")
    print(f"    Likely cause         : {hint}")


def print_history(order_id: str) -> None:
    print("\n── Status history ───────────────────────────────────────")
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/api/orders/{order_id}/history", timeout=5)
        r.raise_for_status()
        for entry in r.json():
            frm = entry.get("fromStatus") or "—"
            to  = entry["toStatus"]
            at  = entry["changedAt"]
            print(f"  {frm:30s} → {to:30s}  {at}")
    except Exception as exc:
        warn(f"Could not fetch history: {exc}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("═══════════════════════════════════════════════════════")
    print("  Sequencer-Orchestrator  —  Round-trip health check")
    print("═══════════════════════════════════════════════════════")

    check_prerequisites()

    print("\n── Setting up test data ─────────────────────────────────")
    patient_id = enroll_patient()
    order_id   = create_order(patient_id)

    print("\n── Starting vendor consumers ────────────────────────────")
    procs = start_vendor_consumers()

    try:
        poll_until_closed(order_id)
        print_history(order_id)
        print(f"\n  [{ts()}] ✓ PASS — full round trip complete, saga reached CLOSED")
        print("═══════════════════════════════════════════════════════\n")
    finally:
        print("\n── Stopping vendor consumers ────────────────────────────")
        for vendor_id, proc in procs:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"  stopped {vendor_id} (pid={proc.pid})")


if __name__ == "__main__":
    main()
