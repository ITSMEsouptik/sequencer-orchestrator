import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    vendor_id: str
    queue_url: str
    sns_topic_arn: str
    step_completion_map: dict[str, str]
    work_delay_seconds: float
    fail_rate: float                          # 0.0–1.0; injects processing failures for DLQ testing
    aws_region: str
    aws_endpoint_url: Optional[str]           # set for LocalStack; omit for real AWS
    idempotency_db_path: str
    monitoring_close_delay_seconds: Optional[int]  # clinical only: seconds after INFUSION_COMPLETE before CASE_CLOSED

    @classmethod
    def from_env(cls) -> "Config":
        raw_map = os.environ["STEP_COMPLETION_MAP"]
        # Format: "STEP_A:COMPLETION_A,STEP_B:COMPLETION_B"
        step_map = {}
        for pair in raw_map.split(","):
            step, completion = pair.strip().split(":")
            step_map[step.strip()] = completion.strip()

        raw_delay = os.environ.get("MONITORING_CLOSE_DELAY_SECONDS")
        monitoring_delay = int(raw_delay) if raw_delay is not None else None

        return cls(
            vendor_id=os.environ["VENDOR_ID"],
            queue_url=os.environ["QUEUE_URL"],
            sns_topic_arn=os.environ["SNS_TOPIC_ARN"],
            step_completion_map=step_map,
            work_delay_seconds=float(os.environ.get("WORK_DELAY_SECONDS", "2")),
            fail_rate=float(os.environ.get("FAIL_RATE", "0.0")),
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            aws_endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
            idempotency_db_path=os.environ.get("IDEMPOTENCY_DB_PATH", "/data/idempotency.db"),
            monitoring_close_delay_seconds=monitoring_delay,
        )
