#!/usr/bin/env python3
"""
Health check for all Sequencer-Orchestrator services.

Checks: Postgres, LocalStack (SQS queues), Spring Boot orchestrator, FastAPI agent.
Exits 0 if every service is UP, 1 if any are DOWN.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --json      # machine-readable output
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

# ── config ────────────────────────────────────────────────────────────────────

ORCHESTRATOR_URL   = os.environ.get("ORCHESTRATOR_URL",   "http://localhost:8080")
AGENT_URL          = os.environ.get("AGENT_URL",          "http://localhost:8090")
LOCALSTACK_URL     = os.environ.get("AWS_ENDPOINT_URL",   "http://localhost:4566")
TIMEOUT            = 5  # seconds per check

# ── result type ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    up: bool
    detail: str = ""


# ── individual checks ─────────────────────────────────────────────────────────

def check_orchestrator() -> CheckResult:
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/api/orders", timeout=TIMEOUT)
        r.raise_for_status()
        return CheckResult("Orchestrator :8080", True)
    except Exception as exc:
        return CheckResult("Orchestrator :8080", False, str(exc))


def check_agent() -> CheckResult:
    try:
        r = requests.get(f"{AGENT_URL}/health", timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        db_ok = body.get("db") == "ok"
        detail = f"db: {body.get('db', '?')}"
        return CheckResult("Agent :8090", db_ok, detail)
    except Exception as exc:
        return CheckResult("Agent :8090", False, str(exc))


def check_localstack() -> CheckResult:
    try:
        sqs = boto3.client(
            "sqs",
            region_name="us-east-1",
            endpoint_url=LOCALSTACK_URL,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        queues = sqs.list_queues(QueueNamePrefix="sequencer").get("QueueUrls", [])
        if not queues:
            return CheckResult("LocalStack :4566", False, "no sequencer queues — run create-queues.sh")
        names = [q.split("/")[-1] for q in queues]
        return CheckResult("LocalStack :4566", True, f"{len(queues)} queues: {', '.join(names)}")
    except (BotoCoreError, ClientError, Exception) as exc:
        return CheckResult("LocalStack :4566", False, str(exc))


def check_all() -> list[CheckResult]:
    """Run all checks and return results. Importable by demo.py."""
    return [
        check_orchestrator(),
        check_agent(),
        check_localstack(),
    ]


# ── formatting ────────────────────────────────────────────────────────────────

_DETAIL_MAX = 58


def _truncate(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 3] + "..."


def _print_table(results: list[CheckResult]) -> None:
    col_name   = max(len(r.name) for r in results) + 2
    col_status = 6
    col_detail = _DETAIL_MAX

    sep = f"+-{'-' * col_name}-+-{'-' * col_status}-+-{'-' * col_detail}-+"
    hdr = f"| {'Service':<{col_name}} | {'Status':<{col_status}} | {'Detail':<{col_detail}} |"

    print(sep)
    print(hdr)
    print(sep)
    for r in results:
        status = "✓ UP  " if r.up else "✗ DOWN"
        detail = _truncate(r.detail, col_detail)
        print(f"| {r.name:<{col_name}} | {status:<{col_status}} | {detail:<{col_detail}} |")
    print(sep)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Sequencer service health check")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    print("\n── Sequencer Health Check ───────────────────────────────────")
    results = check_all()

    if args.json:
        print(json.dumps([{"name": r.name, "up": r.up, "detail": r.detail} for r in results], indent=2))
    else:
        _print_table(results)

    all_up = all(r.up for r in results)
    if all_up:
        print("\n  All services UP\n")
    else:
        down = [r.name for r in results if not r.up]
        print(f"\n  DOWN: {', '.join(down)}\n")

    sys.exit(0 if all_up else 1)


if __name__ == "__main__":
    main()
