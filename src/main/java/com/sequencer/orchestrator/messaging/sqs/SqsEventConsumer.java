package com.sequencer.orchestrator.messaging.sqs;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.sequencer.orchestrator.messaging.events.SequencerEvent;
import com.sequencer.orchestrator.saga.OrderSagaOrchestrator;
import com.sequencer.orchestrator.service.IdempotencyService;

import io.awspring.cloud.sqs.annotation.SqsListener;
import io.awspring.cloud.sqs.annotation.SqsListenerAcknowledgementMode;
import io.awspring.cloud.sqs.listener.acknowledgement.Acknowledgement;

@Component
public class SqsEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(SqsEventConsumer.class);
    
    private final IdempotencyService idempotencyService;

    private final OrderSagaOrchestrator sagaOrchestrator;

    public SqsEventConsumer(IdempotencyService idempotencyService,
            OrderSagaOrchestrator sagaOrchestrator) {
        
        this.idempotencyService = idempotencyService;

        this.sagaOrchestrator = sagaOrchestrator;
    }

    @SqsListener(value = "${sequencer.sqs.main-queue-url}", acknowledgementMode = SqsListenerAcknowledgementMode.MANUAL)
    public void handleMessage(SequencerEvent event, Acknowledgement acknowledgement) {
        log.info("event type {} for {} and event id {}", event.getEventType(), event.getOrderId(), event.getEventId());

        if (idempotencyService.isAlreadyProcessed(event.getEventId())) {
            log.info("Event {} duplication happened", event.getEventId());
            acknowledgement.acknowledge();
            return;
        }

        try {
            sagaOrchestrator.handle(event);
            acknowledgement.acknowledge();
        } catch (Exception e) {
            log.error("Failed to process event {} for order {}: {}",
            event.getEventId(), event.getOrderId(), e.getMessage(), e);
        }

    }
}
