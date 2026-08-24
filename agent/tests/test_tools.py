import json
import sys
import os
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tools


# ── cursor factory helpers ─────────────────────────────────────────────────────

def _cursor_returning(row=None, rows=None):
    """Return a context-manager factory that yields a mock cursor."""
    @contextmanager
    def _factory():
        cur = MagicMock()
        cur.fetchone.return_value = row
        cur.fetchall.return_value = rows if rows is not None else []
        yield cur
    return _factory


# ── get_order_status ──────────────────────────────────────────────────────────

def test_get_order_status_found(monkeypatch):
    row = {
        "id": "ord-1",
        "status": "MANUFACTURING",
        "manufacturing_slot_date": None,
        "apheresis_date": None,
        "infusion_target_date": None,
        "failure_reason": None,
        "created_at": "2026-08-01T10:00:00",
        "updated_at": "2026-08-10T12:00:00",
        "patient_name": "Alice Smith",
        "diagnosis_code": "C91.0",
        "treatment_center_id": "tc-1",
    }
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(row=row))
    result = json.loads(tools.get_order_status("ord-1"))
    assert result["status"] == "MANUFACTURING"
    assert result["patient_name"] == "Alice Smith"


def test_get_order_status_not_found(monkeypatch):
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(row=None))
    result = json.loads(tools.get_order_status("missing-id"))
    assert "error" in result
    assert "missing-id" in result["error"]


# ── get_order_history ─────────────────────────────────────────────────────────

def test_get_order_history_returns_sorted_transitions(monkeypatch):
    rows = [
        {"from_status": None, "to_status": "SLOT_REQUESTED", "changed_at": "2026-08-01T09:00:00"},
        {"from_status": "SLOT_REQUESTED", "to_status": "APHERESIS_SCHEDULED", "changed_at": "2026-08-01T09:01:00"},
        {"from_status": "APHERESIS_SCHEDULED", "to_status": "IN_TRANSIT_INBOUND", "changed_at": "2026-08-05T08:00:00"},
    ]
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=rows))
    result = json.loads(tools.get_order_history("ord-1"))
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["to_status"] == "SLOT_REQUESTED"
    assert result[-1]["to_status"] == "IN_TRANSIT_INBOUND"


def test_get_order_history_empty(monkeypatch):
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=[]))
    result = json.loads(tools.get_order_history("ord-missing"))
    assert "error" in result


# ── find_orders_by_patient ────────────────────────────────────────────────────

def test_find_orders_by_patient_match(monkeypatch):
    rows = [
        {
            "order_id": "ord-1",
            "status": "CLOSED",
            "created_at": "2026-08-01",
            "updated_at": "2026-08-20",
            "patient_id": "pat-1",
            "patient_name": "Bob Jones",
            "diagnosis_code": "C91.0",
        }
    ]
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=rows))
    result = json.loads(tools.find_orders_by_patient("Bob"))
    assert isinstance(result, list)
    assert result[0]["patient_name"] == "Bob Jones"


def test_find_orders_by_patient_no_match(monkeypatch):
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=[]))
    result = json.loads(tools.find_orders_by_patient("Nonexistent"))
    assert "message" in result
    assert "Nonexistent" in result["message"]


# ── list_orders_by_status ─────────────────────────────────────────────────────

def test_list_orders_by_status_found(monkeypatch):
    rows = [
        {
            "order_id": "ord-2",
            "status": "QC_IN_PROGRESS",
            "created_at": "2026-08-15",
            "updated_at": "2026-08-18",
            "patient_name": "Carol White",
            "diagnosis_code": "C91.0",
        }
    ]
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=rows))
    result = json.loads(tools.list_orders_by_status("qc_in_progress"))
    assert result[0]["status"] == "QC_IN_PROGRESS"


def test_list_orders_by_status_empty(monkeypatch):
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=[]))
    result = json.loads(tools.list_orders_by_status("MANUFACTURING"))
    assert "message" in result


def test_list_orders_by_status_uppercases_input(monkeypatch):
    """SQL query receives the status in uppercase regardless of caller casing."""
    captured_args = []

    @contextmanager
    def capturing_cursor():
        cur = MagicMock()
        cur.fetchall.return_value = []
        original_execute = cur.execute

        def capturing_execute(sql, args=None):
            if args:
                captured_args.extend(args)
            return original_execute(sql, args)

        cur.execute = capturing_execute
        yield cur

    monkeypatch.setattr(tools.db, "get_cursor", capturing_cursor)
    tools.list_orders_by_status("manufacturing")
    assert captured_args[0] == "MANUFACTURING"


# ── list_active_orders ────────────────────────────────────────────────────────

def test_list_active_orders_returns_non_terminal(monkeypatch):
    rows = [
        {
            "order_id": "ord-3",
            "status": "INFUSED",
            "created_at": "2026-08-18",
            "updated_at": "2026-08-20",
            "patient_name": "Dan Brown",
            "diagnosis_code": "C91.0",
        }
    ]
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=rows))
    result = json.loads(tools.list_active_orders())
    assert result[0]["status"] == "INFUSED"


def test_list_active_orders_empty(monkeypatch):
    monkeypatch.setattr(tools.db, "get_cursor", _cursor_returning(rows=[]))
    result = json.loads(tools.list_active_orders())
    assert "message" in result
