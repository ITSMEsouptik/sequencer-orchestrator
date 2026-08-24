#!/usr/bin/env python3
"""
End-to-end Sequencer-Orchestrator demo.

Flow:
  1. Health check — fail fast if any service is down
  2. Enroll a patient and create a therapy order
  3. Start all four vendor consumers
  4. Poll saga status until CLOSED (or FAILED / timeout)
  5. Print the raw status history from the DB
  6. Query the FastAPI agent in natural language and print its response

Usage:
    pip install requests boto3
    python scripts/demo.py

Environment overrides (all optional):
    ORCHESTRATOR_URL          default http://localhost:8080
    AGENT_URL                 default http://localhost:8090
    AWS_ENDPOINT_URL          default http://localhost:4566
    SNS_TOPIC_ARN             default arn:aws:sns:us-east-1:000000000000:sequencer-orchestrator-events
    ROUND_TRIP_TIMEOUT        default 120  (seconds)
"""

import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from health_check import check_all, CheckResult

# ── config ────────────────────────────────────────────────────────────────────

ORCHESTRATOR_URL   = os.environ.get("ORCHESTRATOR_URL",  "http://localhost:8080")
AGENT_URL          = os.environ.get("AGENT_URL",         "http://localhost:8090")
LOCALSTACK_URL     = os.environ.get("AWS_ENDPOINT_URL",  "http://localhost:4566")
TOPIC_ARN          = os.environ.get(
    "SNS_TOPIC_ARN",
    "arn:aws:sns:us-east-1:000000000000:sequencer-orchestrator-events",
)
TIMEOUT_SECONDS    = int(os.environ.get("ROUND_TRIP_TIMEOUT", "120"))
POLL_INTERVAL      = 2

VENDOR_CONFIGS = [
    {
        "VENDOR_ID":           "manufacturing",
        "QUEUE_URL":           f"{LOCALSTACK_URL}/000000000000/sequencer-manufacturing-inbound",
        "STEP_COMPLETION_MAP": "MANUFACTURING_SLOT_REQUESTED:MANUFACTURING_SLOT_CONFIRMED,"
                               "MANUFACTURING_STARTED:MANUFACTURING_CRYOPRESERVATION_COMPLETE",
        "WORK_DELAY_SECONDS":  "1",
    },
    {
        "VENDOR_ID":           "logistics",
        "QUEUE_URL":           f"{LOCALSTACK_URL}/000000000000/sequencer-logistics-inbound",
        "STEP_COMPLETION_MAP": "INBOUND_SHIPMENT_DISPATCHED:PRODUCT_ACCESSIONED,"
                               "OUTBOUND_SHIPMENT_DISPATCHED:OUTBOUND_SHIPMENT_RECEIVED",
        "WORK_DELAY_SECONDS":  "1",
    },
    {
        "VENDOR_ID":                      "clinical",
        "QUEUE_URL":                      f"{LOCALSTACK_URL}/000000000000/sequencer-clinical-inbound",
        "STEP_COMPLETION_MAP":            "APHERESIS_SCHEDULED:APHERESIS_COMPLETE,"
                                          "INFUSION_SCHEDULED:INFUSION_COMPLETE",
        "WORK_DELAY_SECONDS":             "1",
        "MONITORING_CLOSE_DELAY_SECONDS": "5",
    },
    {
        "VENDOR_ID":           "qc-lab",
        "QUEUE_URL":           f"{LOCALSTACK_URL}/000000000000/sequencer-qc-lab-inbound",
        "STEP_COMPLETION_MAP": "QC_INITIATED:QC_PASSED",
        "WORK_DELAY_SECONDS":  "1",
    },
]

COMMON_ENV = {
    "SNS_TOPIC_ARN":        TOPIC_ARN,
    "AWS_REGION":           "us-east-1",
    "AWS_ENDPOINT_URL":     LOCALSTACK_URL,
    "AWS_ACCESS_KEY_ID":    "test",
    "AWS_SECRET_ACCESS_KEY":"test",
}

# ── helpers ───────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def banner(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 54 - len(title))}")

def ok(msg: str) -> None:   print(f"  [{ts()}] ✓ {msg}")
def fail(msg: str) -> None: print(f"  [{ts()}] ✗ {msg}"); sys.exit(1)
def warn(msg: str) -> None: print(f"  [{ts()}] ! {msg}")
def info(msg: str) -> None: print(f"  [{ts()}]   {msg}")

# ── steps ─────────────────────────────────────────────────────────────────────

def run_health_check() -> None:
    banner("Health Check")
    results: list[CheckResult] = check_all()
    for r in results:
        icon = "✓" if r.up else "✗"
        detail = f"  ({r.detail})" if r.detail else ""
        print(f"  [{ts()}] {icon} {r.name}{detail}")
    down = [r for r in results if not r.up]
    if down:
        fail(f"Services DOWN: {', '.join(r.name for r in down)} — fix these before running the demo")


def enroll_patient() -> tuple[str, str]:
    unique = uuid.uuid4().hex[:6].upper()
    name = f"Demo Patient {unique}"
    payload = {
        "name":              name,
        "dateOfBirth":       "1972-06-21",
        "diagnosisCode":     "C91.0",
        "hcpID":             str(uuid.uuid4()),
        "treatmentCenterID": str(uuid.uuid4()),
    }
    r = requests.post(f"{ORCHESTRATOR_URL}/api/patients", json=payload, timeout=10)
    if r.status_code not in (200, 201):
        fail(f"Patient enroll failed {r.status_code}: {r.text}")
    patient_id = r.json()["id"]
    ok(f"Patient enrolled  id={patient_id}  name={name}")
    return patient_id, name


def create_order(patient_id: str) -> str:
    payload = {
        "patientId":         patient_id,
        "hcpID":             str(uuid.uuid4()),
        "treatmentCenterID": str(uuid.uuid4()),
    }
    r = requests.post(f"{ORCHESTRATOR_URL}/api/orders", json=payload, timeout=10)
    if r.status_code not in (200, 201):
        fail(f"Order create failed {r.status_code}: {r.text}")
    order_id = r.json()["orderId"]
    ok(f"Order created     id={order_id}  status=SLOT_REQUESTED")
    return order_id


def start_vendors() -> list[tuple[str, subprocess.Popen]]:
    consumer_script = Path(__file__).parent.parent / "vendor-consumer" / "main.py"
    if not consumer_script.exists():
        fail(f"Vendor consumer not found at {consumer_script}")

    procs = []
    for cfg in VENDOR_CONFIGS:
        env = {**os.environ, **COMMON_ENV, **cfg}
        env["IDEMPOTENCY_DB_PATH"] = f"/tmp/demo-{cfg['VENDOR_ID']}-idempotency.db"
        proc = subprocess.Popen(
            [sys.executable, str(consumer_script)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append((cfg["VENDOR_ID"], proc))
        ok(f"Vendor started    {cfg['VENDOR_ID']} (pid={proc.pid})")
    return procs


def poll_until_closed(order_id: str) -> list[str]:
    """Poll saga status until CLOSED. Returns list of statuses seen."""
    deadline = time.time() + TIMEOUT_SECONDS
    last_status = None
    seen: list[str] = []

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
            info(f"→ {status:<30}  +{elapsed}s")
            seen.append(status)
            last_status = status

        if status == "CLOSED":
            return seen
        if status in ("FAILED", "CANCELLED"):
            fail(f"Saga reached {status}")

        time.sleep(POLL_INTERVAL)

    fail(f"Timed out after {TIMEOUT_SECONDS}s — stuck at {last_status}")


def print_raw_history(order_id: str) -> None:
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/api/orders/{order_id}/history", timeout=5)
        r.raise_for_status()
        for entry in r.json():
            frm = entry.get("fromStatus") or "—"
            to  = entry["toStatus"]
            at  = entry["changedAt"]
            print(f"  {frm:<30} → {to:<30}  {at}")
    except Exception as exc:
        warn(f"Could not fetch history: {exc}")


def query_agent(question: str) -> tuple[str, list[str]]:
    payload = {"messages": [{"role": "user", "content": question}]}
    r = requests.post(f"{AGENT_URL}/chat", json=payload, timeout=30)
    r.raise_for_status()
    body = r.json()
    return body["response"], body["tools_used"]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("═" * 60)
    print("  Sequencer-Orchestrator  —  End-to-End Demo")
    print("═" * 60)

    run_health_check()

    banner("Creating Test Data")
    patient_id, patient_name = enroll_patient()
    order_id = create_order(patient_id)

    banner("Starting Vendor Consumers")
    procs = start_vendors()

    try:
        banner(f"Saga Advancing  (timeout={TIMEOUT_SECONDS}s)")
        poll_until_closed(order_id)
        ok(f"Saga reached CLOSED")

        banner("Raw Status History  (from DB via orchestrator)")
        print_raw_history(order_id)

        banner("Agent Natural Language Queries")

        q1 = f"Show me the full history of order {order_id}"
        info(f"Q: {q1}")
        response, tools = query_agent(q1)
        print(f"\n{response}\n")
        info(f"Tools called: {tools}")

        q2 = f"What is the current status of the order for patient {patient_name}?"
        info(f"\nQ: {q2}")
        response, tools = query_agent(q2)
        print(f"\n{response}\n")
        info(f"Tools called: {tools}")

        print("═" * 60)
        print(f"  [{ts()}] ✓ DEMO COMPLETE")
        print("═" * 60)

    finally:
        banner("Stopping Vendor Consumers")
        for vendor_id, proc in procs:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"  stopped {vendor_id} (pid={proc.pid})")


if __name__ == "__main__":
    main()
