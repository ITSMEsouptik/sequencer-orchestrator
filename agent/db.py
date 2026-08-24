from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

_database_url: str = ""


def init(database_url: str) -> None:
    global _database_url
    _database_url = database_url


@contextmanager
def get_cursor():
    conn = psycopg2.connect(_database_url, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()
