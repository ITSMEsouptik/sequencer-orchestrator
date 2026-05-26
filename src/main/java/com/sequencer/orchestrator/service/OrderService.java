package com.sequencer.orchestrator.service;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.sequencer.orchestrator.api.dto.CreateOrderRequest;
import com.sequencer.orchestrator.api.dto.OrderStatusHistoryResponse;
import com.sequencer.orchestrator.api.dto.OrderSummaryResponse;
import com.sequencer.orchestrator.domain.model.entity.OrderStatusHistory;
import com.sequencer.orchestrator.domain.model.entity.OutboxEvent;
import com.sequencer.orchestrator.domain.model.entity.Patient;
import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.AggregatedType;
import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.domain.repository.OrderStatusHistoryRepository;
import com.sequencer.orchestrator.domain.repository.OutboxEventRepository;
import com.sequencer.orchestrator.domain.repository.PatientRepository;
import com.sequencer.orchestrator.domain.repository.TherapyOrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class OrderService {
    private final TherapyOrderRepository therapyOrderRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final PatientRepository patientRepository;
    private final OutboxEventRepository outboxEventRepository;
    private final SSeEmitterRegistry sseEmitterRegistry;

    public OrderService(
            TherapyOrderRepository therapyOrderRepository,
            PatientRepository patientRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            OutboxEventRepository outboxEventRepository,
            SSeEmitterRegistry sseEmitterRegistry) {

        this.therapyOrderRepository = therapyOrderRepository;
        this.patientRepository = patientRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.outboxEventRepository = outboxEventRepository;
        this.sseEmitterRegistry = sseEmitterRegistry;

    }

    @Transactional
    public OrderSummaryResponse createOrder(CreateOrderRequest request) {
        Optional<Patient> patient = patientRepository.findById(request.getPatientId());

        if (patient.isEmpty()) {
            throw new IllegalArgumentException("Patient not found");
        }

        TherapyOrder order = TherapyOrder.builder()
                .patient(patient.get())
                .hcpID(request.getHcpID())
                .treatmentCenterID(request.getTreatmentCenterID())
                .build();

        therapyOrderRepository.save(order);

        OutboxEvent event = OutboxEvent.builder()
                .eventType(EventType.MANUFACTURING_SLOT_REQUESTED)
                .aggregatedID(order.getId())
                .aggregatedType(AggregatedType.THERAPY_ORDER)
                .payload(JsonNodeFactory.instance.objectNode()
                        .put("eventId", UUID.randomUUID().toString()) // ← idempotency key
                        .put("orderId", order.getId().toString())
                        .put("patientId", order.getPatient().getId().toString())
                        .put("status", order.getStatus().toString())
                        .put("timestamp", OffsetDateTime.now().toString()))

                .build();

        outboxEventRepository.save(event);

        OrderStatusHistory history = OrderStatusHistory.builder()
                .orderId(order.getId())
                .fromStatus(null)
                .toStatus(OrderStatus.SLOT_REQUESTED)
                .build();

        orderStatusHistoryRepository.save(history);

        OrderSummaryResponse response = new OrderSummaryResponse(
                order.getId(),
                order.getPatient().getName(),
                order.getStatus(),
                order.getCreatedAt(),
                order.getUpdatedAt());

        sseEmitterRegistry.broadcast(response);
        return response;
    }

    @Transactional(readOnly = true)
    public List<OrderSummaryResponse> getAllOrders(OrderStatus status) {
        List<TherapyOrder> orders;
        if (status != null) {
            orders = therapyOrderRepository.findByStatus(status);
        } else {
            orders = therapyOrderRepository.findAll();
        }

        return orders.stream()
                .map(order -> new OrderSummaryResponse(
                        order.getId(),
                        order.getPatient().getName(),
                        order.getStatus(),
                        order.getCreatedAt(),
                        order.getUpdatedAt()))
                .toList();
    }

    @Transactional(readOnly = true)
    public OrderSummaryResponse getOrderByID(UUID id) {
        Optional<TherapyOrder> order = therapyOrderRepository.findById(id);
        if (order.isEmpty()) {
            throw new IllegalArgumentException("Order Not Found");
        }
        OrderSummaryResponse response = OrderSummaryResponse.builder()
                .orderId(order.get().getId())
                .patientName(order.get().getPatient().getName())
                .status(order.get().getStatus())
                .createdAt(order.get().getCreatedAt())
                .updatedAt(order.get().getUpdatedAt())
                .build();
        return response;
    }

    @Transactional(readOnly = true)
    public List<OrderStatusHistoryResponse> getStatusHistory(UUID id) {
        List<OrderStatusHistory> history = orderStatusHistoryRepository.findByOrderIdOrderByChangedAtAsc(id);
        return history.stream()
                .map(h -> new OrderStatusHistoryResponse(
                        h.getFromStatus(),
                        h.getToStatus(),
                        h.getChangedAt()))
                .toList();
    }
}
