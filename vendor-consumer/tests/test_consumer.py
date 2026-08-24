import json
import sys
import os
import pytest
from unittest.mock import MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from consumer import VendorConsumer, _derive_completion_event_id
from idempotency import IdempotencyStore


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mfg_config():
    return Config(
        vendor_id="manufacturing",
        queue_url="http://localhost:4566/000000000000/test-queue",
        sns_topic_arn="arn:aws:sns:us-east-1:000000000000:test-topic",
        step_completion_map={
            "MANUFACTURING_SLOT_REQUESTED": "MANUFACTURING_SLOT_CONFIRMED",
            "MANUFACTURING_STARTED": "MANUFACTURING_CRYOPRESERVATION_COMPLETE",
        },
        work_delay_seconds=0,
        fail_rate=0.0,
        aws_region="us-east-1",
        aws_endpoint_url="http://localhost:4566",
        idempotency_db_path=":memory:",
        monitoring_close_delay_seconds=None,
    )


@pytest.fixture
def clinical_config():
    return Config(
        vendor_id="clinical",
        queue_url="http://localhost:4566/000000000000/clinical-queue",
        sns_topic_arn="arn:aws:sns:us-east-1:000000000000:test-topic",
        step_completion_map={"INFUSION_SCHEDULED": "INFUSION_COMPLETE"},
        work_delay_seconds=0,
        fail_rate=0.0,
        aws_region="us-east-1",
        aws_endpoint_url=None,
        idempotency_db_path=":memory:",
        monitoring_close_delay_seconds=0,  # 0 so tests run instantly
    )


@pytest.fixture
def idempotency(tmp_path):
    return IdempotencyStore(str(tmp_path / "test.db"))


def _make_sqs_msg(event: dict, receipt: str = "rh-abc") -> dict:
    """Wraps event dict in an SNS notification envelope, as SQS delivers it."""
    envelope = json.dumps({"Type": "Notification", "Message": json.dumps(event)})
    return {"Body": envelope, "ReceiptHandle": receipt}


def _base_event(event_type: str, event_id: str = "evt-1") -> dict:
    return {
        "eventId":        event_id,
        "eventType":      event_type,
        "aggregatedId":   "order-uuid-1",
        "aggregatedType": "THERAPY_ORDER",
        "orderId":        "order-uuid-1",
        "patientId":      "patient-uuid-1",
        "status":         "SLOT_REQUESTED",
        "timestamp":      "2026-08-21T00:00:00+00:00",
    }


def _make_consumer(config: Config, idempotency: IdempotencyStore) -> VendorConsumer:
    c = VendorConsumer(config, idempotency)
    c.sqs = MagicMock()
    c.sns = MagicMock()
    return c


# ── happy path ───────────────────────────────────────────────────────────────

def test_known_event_publishes_completion_and_acks(mfg_config, idempotency):
    consumer = _make_consumer(mfg_config, idempotency)
    consumer._process_message(_make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED")))

    consumer.sns.publish.assert_called_once()
    kwargs = consumer.sns.publish.call_args.kwargs
    assert kwargs["MessageAttributes"]["eventType"]["StringValue"] == "MANUFACTURING_SLOT_CONFIRMED"
    body = json.loads(kwargs["Message"])
    assert body["eventType"] == "MANUFACTURING_SLOT_CONFIRMED"
    assert body["aggregatedId"] == "order-uuid-1"
    assert body["orderId"] == "order-uuid-1"
    assert body["patientId"] == "patient-uuid-1"
    consumer.sqs.delete_message.assert_called_once()


def test_completion_event_id_is_deterministic(mfg_config, idempotency):
    """Same step eventId + completion type always produces the same completion eventId."""
    id1 = _derive_completion_event_id("step-evt-abc", "MANUFACTURING_SLOT_CONFIRMED")
    id2 = _derive_completion_event_id("step-evt-abc", "MANUFACTURING_SLOT_CONFIRMED")
    assert id1 == id2


def test_different_completion_types_produce_different_ids():
    id1 = _derive_completion_event_id("step-evt-abc", "MANUFACTURING_SLOT_CONFIRMED")
    id2 = _derive_completion_event_id("step-evt-abc", "MANUFACTURING_CRYOPRESERVATION_COMPLETE")
    assert id1 != id2


# ── idempotency ───────────────────────────────────────────────────────────────

def test_duplicate_event_acks_without_publishing(mfg_config, idempotency):
    consumer = _make_consumer(mfg_config, idempotency)
    msg = _make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED", event_id="dup-1"))

    consumer._process_message(msg)           # first delivery — processes
    consumer.sns.reset_mock()
    consumer.sqs.reset_mock()

    consumer._process_message(msg)           # redelivery — duplicate
    consumer.sns.publish.assert_not_called()
    consumer.sqs.delete_message.assert_called_once()


def test_idempotency_key_not_written_if_publish_fails(mfg_config, idempotency):
    """If SNS publish throws, the eventId must NOT be marked processed so redelivery can retry."""
    consumer = _make_consumer(mfg_config, idempotency)
    consumer.sns.publish.side_effect = RuntimeError("SNS unavailable")

    consumer._process_message(_make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED", event_id="fail-evt")))

    assert not idempotency.is_already_processed("fail-evt")
    consumer.sqs.delete_message.assert_not_called()


# ── unknown / no-op events ────────────────────────────────────────────────────

def test_unknown_event_type_is_skipped_and_acked(mfg_config, idempotency):
    """An event this vendor doesn't handle (e.g. echo from own publish) is acked without publishing."""
    consumer = _make_consumer(mfg_config, idempotency)
    consumer._process_message(_make_sqs_msg(_base_event("QC_INITIATED")))

    consumer.sns.publish.assert_not_called()
    consumer.sqs.delete_message.assert_called_once()


def test_malformed_body_does_not_ack(mfg_config, idempotency):
    consumer = _make_consumer(mfg_config, idempotency)
    consumer._process_message({"Body": "not-json", "ReceiptHandle": "rh-bad"})

    consumer.sns.publish.assert_not_called()
    consumer.sqs.delete_message.assert_not_called()


# ── failure injection / DLQ ───────────────────────────────────────────────────

def test_injected_failure_does_not_ack(mfg_config, idempotency):
    """fail_rate=1.0 → every message fails → no ack → message redelivers → eventually DLQ."""
    config = Config(**{**mfg_config.__dict__, "fail_rate": 1.0})
    consumer = _make_consumer(config, idempotency)
    consumer._process_message(_make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED")))

    consumer.sns.publish.assert_not_called()
    consumer.sqs.delete_message.assert_not_called()


def test_sns_failure_does_not_ack(mfg_config, idempotency):
    consumer = _make_consumer(mfg_config, idempotency)
    consumer.sns.publish.side_effect = RuntimeError("timeout")
    consumer._process_message(_make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED")))

    consumer.sqs.delete_message.assert_not_called()


# ── clinical: INFUSION_SCHEDULED sends two completions ───────────────────────

def test_clinical_sends_infusion_complete_then_case_closed(clinical_config, idempotency):
    consumer = _make_consumer(clinical_config, idempotency)
    event = _base_event("INFUSION_SCHEDULED", event_id="inf-1")
    event["status"] = "INFUSION_READY"
    consumer._process_message(_make_sqs_msg(event))

    assert consumer.sns.publish.call_count == 2
    published_types = [
        json.loads(c.kwargs["Message"])["eventType"]
        for c in consumer.sns.publish.call_args_list
    ]
    assert published_types == ["INFUSION_COMPLETE", "CASE_CLOSED"]
    consumer.sqs.delete_message.assert_called_once()


def test_clinical_case_closed_has_deterministic_event_id(clinical_config, idempotency):
    """CASE_CLOSED eventId is derived from the step eventId — same on redelivery."""
    consumer = _make_consumer(clinical_config, idempotency)
    event = _base_event("INFUSION_SCHEDULED", event_id="inf-2")
    consumer._process_message(_make_sqs_msg(event))

    case_closed_call = consumer.sns.publish.call_args_list[1]
    case_closed_body = json.loads(case_closed_call.kwargs["Message"])
    expected_id = _derive_completion_event_id("inf-2", "CASE_CLOSED")
    assert case_closed_body["eventId"] == expected_id


def test_non_clinical_vendor_does_not_send_case_closed(mfg_config, idempotency):
    """Only clinical (INFUSION_SCHEDULED + monitoring_close_delay_seconds set) sends CASE_CLOSED."""
    consumer = _make_consumer(mfg_config, idempotency)
    consumer._process_message(_make_sqs_msg(_base_event("MANUFACTURING_SLOT_REQUESTED")))

    assert consumer.sns.publish.call_count == 1
    body = json.loads(consumer.sns.publish.call_args.kwargs["Message"])
    assert body["eventType"] == "MANUFACTURING_SLOT_CONFIRMED"
