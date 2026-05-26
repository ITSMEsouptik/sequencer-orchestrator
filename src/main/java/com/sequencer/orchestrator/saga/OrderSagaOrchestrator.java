package com.sequencer.orchestrator.saga;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.sequencer.orchestrator.api.dto.OrderSummaryResponse;
import com.sequencer.orchestrator.domain.model.entity.OutboxEvent;
import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.AggregatedType;
import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.domain.repository.OutboxEventRepository;
import com.sequencer.orchestrator.domain.repository.TherapyOrderRepository;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;
import com.sequencer.orchestrator.service.SSeEmitterRegistry;

@Component
public class OrderSagaOrchestrator {
    private final Map<EventType, SagaStepHandler> handlers;
    private final TherapyOrderRepository therapyOrderRepository;
    private final OutboxEventRepository outboxEventRepository;
    private final SSeEmitterRegistry sseEmitterRegistry;
    private static final Logger log = LoggerFactory.getLogger(OrderSagaOrchestrator.class);

    public OrderSagaOrchestrator(
            List<SagaStepHandler> handlers,
            TherapyOrderRepository therapyOrderRepository,
            OutboxEventRepository outboxEventRepository,
            SSeEmitterRegistry sseEmitterRegistry
        ) {
        this.handlers = handlers.stream()
                .collect(Collectors.toMap(SagaStepHandler::handlesEvent, h -> h));

        this.therapyOrderRepository = therapyOrderRepository;
        this.outboxEventRepository = outboxEventRepository;
        this.sseEmitterRegistry = sseEmitterRegistry;
    }

    @Transactional
    public void handle(SequencerEvent event) {
        log.info("Saga received event {} for order {}", event.getEventType(), event.getOrderId());

        SagaStepHandler handler = handlers.get(event.getEventType());
        if (handler == null) {
            log.error("Handler is unknown");
            return;
        }

        Optional<TherapyOrder> order = therapyOrderRepository.findById(UUID.fromString(event.getAggregatedId()));

        if (order.isEmpty()) {
            log.error("Order not found for aggregatedId {}", event.getAggregatedId());
            return;
        }

        TherapyOrder therapyOrder = order.get();
        SagaResult result = handler.handle(event, therapyOrder);

        if (result.isSuccess()) {
            therapyOrder.advanceTo(result.getNextStatus());
            therapyOrderRepository.save(therapyOrder);
            sseEmitterRegistry.broadcast(toSummary(therapyOrder));

            if (result.getNextEventType() != null) {
                outboxEventRepository.save(buildOutboxEvent(result.getNextEventType(), therapyOrder));
            }
        } else {
            therapyOrder.advanceTo(OrderStatus.FAILED);
            therapyOrderRepository.save(therapyOrder);
            sseEmitterRegistry.broadcast(toSummary(therapyOrder));
            outboxEventRepository.save(buildOutboxEvent(EventType.ORDER_FAILED, therapyOrder));
        }
    }

    private OrderSummaryResponse toSummary(TherapyOrder order) {
        return OrderSummaryResponse.builder()
                .orderId(order.getId())
                .patientName(order.getPatient().getName())
                .status(order.getStatus())
                .createdAt(order.getCreatedAt())
                .updatedAt(order.getUpdatedAt())
                .build();
    }

    private OutboxEvent buildOutboxEvent(EventType eventType, TherapyOrder order) {
        return OutboxEvent.builder()
                .eventType(eventType)
                .aggregatedID(order.getId())
                .aggregatedType(AggregatedType.THERAPY_ORDER)
                .payload(JsonNodeFactory.instance.objectNode()
                        .put("eventId", UUID.randomUUID().toString())
                        .put("orderId", order.getId().toString())
                        .put("patientId", order.getPatient().getId().toString())
                        .put("status", order.getStatus().toString())
                        .put("timestamp", OffsetDateTime.now().toString()))
                .build();
    }
}
