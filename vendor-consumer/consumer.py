import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

from config import Config
from idempotency import IdempotencyStore
from models import SequencerEvent

log = logging.getLogger(__name__)


def _derive_completion_event_id(step_event_id: str, completion_type: str) -> str:
    """
    Deterministic UUID from step eventId + completion type.
    Ensures the orchestrator's idempotency service deduplicates correctly
    if the vendor consumer redelivers the same completion event after a crash.
    """
    key = f"{step_event_id}|{completion_type}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


class VendorConsumer:
    def __init__(self, config: Config, idempotency: IdempotencyStore):
        self.config = config
        self.idempotency = idempotency
        boto_kwargs = {"region_name": config.aws_region}
        if config.aws_endpoint_url:
            boto_kwargs["endpoint_url"] = config.aws_endpoint_url
        self.sqs = boto3.client("sqs", **boto_kwargs)
        self.sns = boto3.client("sns", **boto_kwargs)

    def run(self) -> None:
        log.info("vendor=%s queue=%s starting poll loop", self.config.vendor_id, self.config.queue_url)
        while True:
            self._poll_once()

    def _poll_once(self) -> None:
        try:
            resp = self.sqs.receive_message(
                QueueUrl=self.config.queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                MessageAttributeNames=["All"],
            )
            for msg in resp.get("Messages", []):
                try:
                    self._process_message(msg)
                except Exception:
                    log.exception("vendor=%s unexpected error on message — leaving in-flight", self.config.vendor_id)
        except Exception:
            log.exception("vendor=%s SQS receive failed — retrying in 5s", self.config.vendor_id)
            time.sleep(5)

    def _process_message(self, msg: dict) -> None:
        receipt = msg["ReceiptHandle"]

        # SNS wraps the payload in a notification envelope when delivering to SQS.
        try:
            outer = json.loads(msg["Body"])
            body_str = outer.get("Message", msg["Body"])
            body = json.loads(body_str)
            event = SequencerEvent(**body)
        except Exception as exc:
            log.error("vendor=%s failed to parse message body: %s", self.config.vendor_id, exc)
            return  # leave in-flight; malformed messages go to DLQ after maxReceiveCount

        log.info(
            "vendor=%s received eventType=%s orderId=%s eventId=%s",
            self.config.vendor_id, event.eventType, event.orderId, event.eventId,
        )

        # Already processed → safe to ack without re-publishing.
        if self.idempotency.is_already_processed(event.eventId):
            log.info("vendor=%s duplicate eventId=%s — acking without action", self.config.vendor_id, event.eventId)
            self._ack(receipt)
            return

        completion_event_type = self.config.step_completion_map.get(event.eventType)
        if completion_event_type is None:
            # Event arrived but this vendor has no completion for it (e.g., echo from own publish).
            log.debug("vendor=%s no completion mapping for eventType=%s — skipping", self.config.vendor_id, event.eventType)
            self.idempotency.mark_processed(event.eventId)
            self._ack(receipt)
            return

        # Simulate processing time.
        if self.config.work_delay_seconds > 0:
            time.sleep(self.config.work_delay_seconds)

        # Inject failure for DLQ testing (fail_rate=1.0 always fails).
        if self.config.fail_rate > 0 and random.random() < self.config.fail_rate:
            log.warning(
                "vendor=%s injecting failure for eventId=%s (message will redeliver)",
                self.config.vendor_id, event.eventId,
            )
            return  # no ack, no idempotency mark → redelivers until DLQ

        try:
            self._publish_completion(event, completion_event_type)

            # Clinical: after INFUSION_COMPLETE, send CASE_CLOSED after the monitoring window.
            if (
                event.eventType == "INFUSION_SCHEDULED"
                and self.config.monitoring_close_delay_seconds is not None
            ):
                delay = self.config.monitoring_close_delay_seconds
                log.info("vendor=%s monitoring window — sending CASE_CLOSED in %ds", self.config.vendor_id, delay)
                if delay > 0:
                    time.sleep(delay)
                self._publish_completion(event, "CASE_CLOSED")

            self.idempotency.mark_processed(event.eventId)
            self._ack(receipt)

        except Exception:
            log.exception(
                "vendor=%s failed to publish completion for eventId=%s — message will redeliver",
                self.config.vendor_id, event.eventId,
            )
            # No ack → SQS visibility timeout expires → redelivery → idempotency check
            # uses deterministic completion eventId so orchestrator deduplicates correctly.

    def _publish_completion(self, step_event: SequencerEvent, completion_event_type: str) -> None:
        completion_event_id = _derive_completion_event_id(step_event.eventId, completion_event_type)
        payload = {
            "eventId":        completion_event_id,
            "eventType":      completion_event_type,
            "aggregatedId":   step_event.aggregatedId,
            "aggregatedType": step_event.aggregatedType,
            "orderId":        step_event.orderId,
            "patientId":      step_event.patientId,
            "status":         step_event.status,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        self.sns.publish(
            TopicArn=self.config.sns_topic_arn,
            Message=json.dumps(payload),
            MessageAttributes={
                "eventType": {
                    "DataType":    "String",
                    "StringValue": completion_event_type,
                }
            },
        )
        log.info(
            "vendor=%s published eventType=%s orderId=%s completionEventId=%s",
            self.config.vendor_id, completion_event_type, step_event.orderId, completion_event_id,
        )

    def _ack(self, receipt: str) -> None:
        self.sqs.delete_message(QueueUrl=self.config.queue_url, ReceiptHandle=receipt)
        log.debug("vendor=%s acked receipt=%s", self.config.vendor_id, receipt[:20])
