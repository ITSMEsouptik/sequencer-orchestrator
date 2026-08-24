#!/bin/bash
set -e

REGION=us-east-1
ACCOUNT=000000000000

# ── SNS topic ────────────────────────────────────────────────────────────────
TOPIC_ARN=$(awslocal sns create-topic --name sequencer-orchestrator-events \
  --query TopicArn --output text)
echo "SNS topic: $TOPIC_ARN"

# ── Orchestrator inbound queue (no filter policy — receives all events) ───────
awslocal sqs create-queue --queue-name sequencer-orchestrator-main
awslocal sqs create-queue --queue-name sequencer-orchestrator-dlq

ORCH_QUEUE_ARN="arn:aws:sqs:$REGION:$ACCOUNT:sequencer-orchestrator-main"
awslocal sns subscribe \
  --topic-arn "$TOPIC_ARN" \
  --protocol sqs \
  --notification-endpoint "$ORCH_QUEUE_ARN"

echo "Orchestrator queue subscribed (no filter — receives all events)"

# ── Vendor queues with SNS filter policies ───────────────────────────────────
create_vendor_queue() {
  local NAME=$1
  local FILTER_JSON=$2

  awslocal sqs create-queue --queue-name "$NAME"
  awslocal sqs create-queue --queue-name "${NAME}-dlq"

  local QUEUE_ARN="arn:aws:sqs:$REGION:$ACCOUNT:$NAME"
  local SUB_ARN=$(awslocal sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol sqs \
    --notification-endpoint "$QUEUE_ARN" \
    --query SubscriptionArn --output text)

  awslocal sns set-subscription-attributes \
    --subscription-arn "$SUB_ARN" \
    --attribute-name FilterPolicy \
    --attribute-value "$FILTER_JSON"

  awslocal sns set-subscription-attributes \
    --subscription-arn "$SUB_ARN" \
    --attribute-name FilterPolicyScope \
    --attribute-value MessageAttributes

  echo "Vendor queue $NAME subscribed with filter: $FILTER_JSON"
}

create_vendor_queue "sequencer-manufacturing-inbound" \
  '{"eventType":["MANUFACTURING_SLOT_REQUESTED","MANUFACTURING_STARTED"]}'

create_vendor_queue "sequencer-logistics-inbound" \
  '{"eventType":["INBOUND_SHIPMENT_DISPATCHED","OUTBOUND_SHIPMENT_DISPATCHED"]}'

create_vendor_queue "sequencer-clinical-inbound" \
  '{"eventType":["APHERESIS_SCHEDULED","INFUSION_SCHEDULED"]}'

create_vendor_queue "sequencer-qc-lab-inbound" \
  '{"eventType":["QC_INITIATED"]}'

echo "All queues and subscriptions ready."
