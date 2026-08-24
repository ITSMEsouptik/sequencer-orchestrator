import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from idempotency import IdempotencyStore


@pytest.fixture
def store(tmp_path):
    return IdempotencyStore(str(tmp_path / "idempotency.db"))


def test_new_event_is_not_processed(store):
    assert store.is_already_processed("evt-new") is False


def test_marked_event_is_processed(store):
    store.mark_processed("evt-1")
    assert store.is_already_processed("evt-1") is True


def test_mark_is_idempotent(store):
    store.mark_processed("evt-2")
    store.mark_processed("evt-2")  # second call must not raise
    assert store.is_already_processed("evt-2") is True


def test_different_events_are_independent(store):
    store.mark_processed("evt-a")
    assert store.is_already_processed("evt-b") is False


def test_check_does_not_mark(store):
    store.is_already_processed("evt-check")
    assert store.is_already_processed("evt-check") is False
