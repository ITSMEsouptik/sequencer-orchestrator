package com.sequencer.orchestrator.saga;

import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;

import lombok.Getter;

@Getter
public class SagaResult {
    private final boolean success;
    private final OrderStatus nextStatus;
    private final EventType nextEventType;
    private final String errorReason;

    private SagaResult(
            boolean success,
            OrderStatus nextStatus,
            EventType nextEventType,
            String errorReason) {
        this.success = success;
        this.nextStatus = nextStatus;
        this.nextEventType = nextEventType;
        this.errorReason = errorReason;
    }

    public static SagaResult success(OrderStatus nextStatus, EventType nextEventType) {
        return new SagaResult(true, nextStatus, nextEventType, null);
    }

    public static SagaResult failure(String errorReason) {
        return new SagaResult(false, null, null, errorReason);
    }

}
