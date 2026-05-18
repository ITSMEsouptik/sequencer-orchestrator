package com.sequencer.orchestrator.service;

import com.sequencer.orchestrator.domain.model.entity.OrderStatusHistory;
import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.domain.repository.OrderStatusHistoryRepository;
import com.sequencer.orchestrator.domain.repository.TherapyOrderRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Component
public class OrderPollingOrchestrator {
    private static final Logger log = LoggerFactory.getLogger(OrderPollingOrchestrator.class);
    private final TherapyOrderRepository therapyOrderRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;

    public OrderPollingOrchestrator(
            TherapyOrderRepository therapyOrderRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository) {
        this.therapyOrderRepository = therapyOrderRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
    }

    @Scheduled(fixedDelay = 5000)
    @Transactional
    public void pollAndAdvance() {
        List<TherapyOrder> activeOrders = therapyOrderRepository
                .findByStatusNotIn(List.of(OrderStatus.CANCELLED, OrderStatus.CLOSED, OrderStatus.FAILED));

        for (TherapyOrder order : activeOrders) {
            try {
                OrderStatus current = order.getStatus();
                OrderStatus next = switch (current) {
                    case ENROLLED -> OrderStatus.SLOT_REQUESTED;
                    case SLOT_REQUESTED -> OrderStatus.APHERESIS_SCHEDULED;
                    case APHERESIS_SCHEDULED -> OrderStatus.APHERESIS_COMPLETE;
                    case APHERESIS_COMPLETE -> OrderStatus.IN_TRANSIT_INBOUND;
                    case IN_TRANSIT_INBOUND -> OrderStatus.ACCESSIONED;
                    case ACCESSIONED -> OrderStatus.MANUFACTURING;
                    case MANUFACTURING -> OrderStatus.QC_IN_PROGRESS;
                    case QC_IN_PROGRESS -> OrderStatus.RELEASED;
                    case RELEASED -> OrderStatus.IN_TRANSIT_OUTBOUND;
                    case IN_TRANSIT_OUTBOUND -> OrderStatus.RECEIVED_AT_CENTER;
                    case RECEIVED_AT_CENTER -> OrderStatus.LYMPHODEPLETION;
                    case LYMPHODEPLETION -> OrderStatus.INFUSION_READY;
                    case INFUSION_READY -> OrderStatus.INFUSED;
                    case INFUSED -> OrderStatus.MONITORING;
                    case MONITORING -> OrderStatus.CLOSED;
                    default -> null;
                };

                if (next == null)
                    continue;
                log.info("Advancing order {} from {} to {}", order.getId(), current, next);
                order.advanceTo(next);
                therapyOrderRepository.save(order);
                OrderStatusHistory history = OrderStatusHistory
                        .builder()
                        .orderId(order.getId())
                        .fromStatus(current)
                        .toStatus(next)
                        .build();
                orderStatusHistoryRepository.save(history);

            } catch (Exception e) {
                log.error("Failed to advance order {}: {}", order.getId(), e.getMessage());
            }
        }
    }
}
