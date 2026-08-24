FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

# /data is the SQLite idempotency store; mount a volume for persistence across restarts.
VOLUME ["/data"]

# Required env vars (all others have defaults — see config.py):
#   VENDOR_ID              e.g. manufacturing
#   QUEUE_URL              SQS queue URL for this vendor
#   SNS_TOPIC_ARN          the sequencer-events SNS topic ARN
#   STEP_COMPLETION_MAP    "STEP_A:COMPLETION_A,STEP_B:COMPLETION_B"
#
# Optional:
#   WORK_DELAY_SECONDS     simulated processing time (default 2)
#   FAIL_RATE              0.0–1.0 failure injection for DLQ testing (default 0.0)
#   MONITORING_CLOSE_DELAY_SECONDS  clinical only: seconds before CASE_CLOSED (omit to disable)
#   AWS_REGION             (default us-east-1)
#   AWS_ENDPOINT_URL       set for LocalStack, omit for real AWS
#   IDEMPOTENCY_DB_PATH    (default /data/idempotency.db)

CMD ["python", "main.py"]
