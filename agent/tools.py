import json

import db


def get_order_status(order_id: str) -> str:
    """Get the current status and details of a therapy order by its ID."""
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.id,
                o.status,
                o.manufacturing_slot_date,
                o.apheresis_date,
                o.infusion_target_date,
                o.failure_reason,
                o.created_at,
                o.updated_at,
                p.name        AS patient_name,
                p.diagnosis_code,
                p.treatment_center_id
            FROM therapy_orders o
            JOIN patients p ON p.id = o.patient_id
            WHERE o.id = %s
            """,
            (order_id,),
        )
        row = cur.fetchone()
    if row is None:
        return json.dumps({"error": f"No order found with ID '{order_id}'"})
    return json.dumps(dict(row), default=str)


def get_order_history(order_id: str) -> str:
    """Get the full audit trail of status transitions for a therapy order, oldest first."""
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT from_status, to_status, changed_at
            FROM order_status_history
            WHERE order_id = %s
            ORDER BY changed_at ASC
            """,
            (order_id,),
        )
        rows = cur.fetchall()
    if not rows:
        return json.dumps({"error": f"No history found for order '{order_id}'"})
    return json.dumps([dict(r) for r in rows], default=str)


def find_orders_by_patient(patient_name: str) -> str:
    """Find therapy orders for a patient by name (case-insensitive partial match)."""
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.id          AS order_id,
                o.status,
                o.created_at,
                o.updated_at,
                p.id          AS patient_id,
                p.name        AS patient_name,
                p.diagnosis_code
            FROM therapy_orders o
            JOIN patients p ON p.id = o.patient_id
            WHERE p.name ILIKE %s
            ORDER BY o.created_at DESC
            """,
            (f"%{patient_name}%",),
        )
        rows = cur.fetchall()
    if not rows:
        return json.dumps({"message": f"No orders found for patient matching '{patient_name}'"})
    return json.dumps([dict(r) for r in rows], default=str)


def list_orders_by_status(status: str) -> str:
    """List all therapy orders currently in a specific status."""
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.id     AS order_id,
                o.status,
                o.created_at,
                o.updated_at,
                p.name   AS patient_name,
                p.diagnosis_code
            FROM therapy_orders o
            JOIN patients p ON p.id = o.patient_id
            WHERE o.status = %s
            ORDER BY o.updated_at DESC
            """,
            (status.upper(),),
        )
        rows = cur.fetchall()
    if not rows:
        return json.dumps({"message": f"No orders currently in status '{status.upper()}'"})
    return json.dumps([dict(r) for r in rows], default=str)


def list_active_orders() -> str:
    """List all therapy orders not yet in a terminal state (CLOSED, FAILED, CANCELLED)."""
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.id     AS order_id,
                o.status,
                o.created_at,
                o.updated_at,
                p.name   AS patient_name,
                p.diagnosis_code
            FROM therapy_orders o
            JOIN patients p ON p.id = o.patient_id
            WHERE o.status NOT IN ('CLOSED', 'FAILED', 'CANCELLED')
            ORDER BY o.updated_at DESC
            """
        )
        rows = cur.fetchall()
    if not rows:
        return json.dumps({"message": "No active orders found"})
    return json.dumps([dict(r) for r in rows], default=str)


# ── OpenAI tool schemas ────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": (
                "Get the current status and details of a therapy order by its UUID. "
                "Returns patient name, diagnosis, all key dates, and failure reason if any."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "UUID of the therapy order",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_history",
            "description": (
                "Get the full chronological audit trail of status transitions for a therapy "
                "order. Shows every from→to status change with timestamps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "UUID of the therapy order",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_orders_by_patient",
            "description": (
                "Find therapy orders for a patient by searching their name. "
                "Case-insensitive partial match — 'alice' matches 'Alice Smith'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Patient full name or partial name",
                    }
                },
                "required": ["patient_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders_by_status",
            "description": (
                "List all therapy orders currently in a specific status. "
                "Valid statuses: SLOT_REQUESTED, APHERESIS_SCHEDULED, IN_TRANSIT_INBOUND, "
                "ACCESSIONED, MANUFACTURING, QC_IN_PROGRESS, RELEASED, IN_TRANSIT_OUTBOUND, "
                "RECEIVED_AT_CENTER, INFUSED, MONITORING, CLOSED, FAILED, CANCELLED."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Order status to filter by (case-insensitive)",
                    }
                },
                "required": ["status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_active_orders",
            "description": (
                "List all therapy orders that are still in-progress "
                "(not yet CLOSED, FAILED, or CANCELLED)."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

TOOL_DISPATCH: dict[str, callable] = {
    "get_order_status": get_order_status,
    "get_order_history": get_order_history,
    "find_orders_by_patient": find_orders_by_patient,
    "list_orders_by_status": list_orders_by_status,
    "list_active_orders": list_active_orders,
}
