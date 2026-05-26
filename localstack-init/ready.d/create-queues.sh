#!/bin/bash
awslocal sqs create-queue --queue-name sequencer-orchestrator-main
awslocal sqs create-queue --queue-name sequencer-orchestrator-dlq
echo "SQS queues created."
