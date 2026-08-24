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
import com.sequencer.orchestrator.domain.model.entity.OrderStatusHistory;
import com.sequencer.orchestrator.domain.repository.OrderStatusHistoryRepository;
import com.sequencer.orchestrator.domain.repository.OutboxEventRepository;
import com.sequencer.orchestrator.domain.repository.TherapyOrderRepository;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;
import com.sequencer.orchestrator.service.SSeEmitterRegistry;

@Component
public class OrderSagaOrchestrator {
    private final Map<EventType, SagaStepHandler> handlers;
    private final TherapyOrderRepository therapyOrderRepository;
    private final OutboxEventRepository outboxEventRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final SSeEmitterRegistry sseEmitterRegistry;
    private static final Logger log = LoggerFactory.getLogger(OrderSagaOrchestrator.class);

    public OrderSagaOrchestrator(
            List<SagaStepHandler> handlers,
            TherapyOrderRepository therapyOrderRepository,
            OutboxEventRepository outboxEventRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            SSeEmitterRegistry sseEmitterRegistry
        ) {
        this.handlers = handlers.stream()
                .collect(Collectors.toMap(SagaStepHandler::handlesEvent, h -> h));

        this.therapyOrderRepository = therapyOrderRepository;
        this.outboxEventRepository = outboxEventRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.sseEmitterRegistry = sseEmitterRegistry;
    }

    @Transactional
    public void handle(SequencerEvent event) {
        log.info("Saga received event {} for order {}", event.getEventType(), event.getOrderId());

        SagaStepHandler handler = handlers.get(event.getEventType());
        if (handler == null) {
            // Expected for events the orchestrator emits (self-echo on the unfiltered inbound queue).
            // Not an error — just no inbound action for this event type.
            log.debug("No handler for eventType {}; skipping", event.getEventType());
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
            OrderStatus previous = therapyOrder.getStatus();
            therapyOrder.advanceTo(result.getNextStatus());
            therapyOrderRepository.save(therapyOrder);
            orderStatusHistoryRepository.save(buildHistory(therapyOrder.getId(), previous, result.getNextStatus()));
            sseEmitterRegistry.broadcast(toSummary(therapyOrder));

            if (result.getNextEventType() != null) {
                outboxEventRepository.save(buildOutboxEvent(result.getNextEventType(), therapyOrder));
            }
        } else {
            OrderStatus previous = therapyOrder.getStatus();
            therapyOrder.advanceTo(OrderStatus.FAILED);
            therapyOrderRepository.save(therapyOrder);
            orderStatusHistoryRepository.save(buildHistory(therapyOrder.getId(), previous, OrderStatus.FAILED));
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

    private OrderStatusHistory buildHistory(UUID orderId, OrderStatus from, OrderStatus to) {
        return OrderStatusHistory.builder()
                .orderId(orderId)
                .fromStatus(from)
                .toStatus(to)
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
