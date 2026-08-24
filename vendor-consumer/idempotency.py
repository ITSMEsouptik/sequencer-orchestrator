import sqlite3
import threading


class IdempotencyStore:
    """
    SQLite-backed seen-event log. Survives container restarts.
    Separates check from mark so the consumer only records an eventId
    after a successful publish — redelivery after a mid-flight crash
    can still produce a completion event (with a deterministic eventId
    the orchestrator will deduplicate on its side).
    """

    def __init__(self, db_path: str = "/data/idempotency.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id     TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    def is_already_processed(self, event_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
            )
            return cur.fetchone() is not None

    def mark_processed(self, event_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO processed_events(event_id) VALUES (?)", (event_id,)
            )
            self._conn.commit()
