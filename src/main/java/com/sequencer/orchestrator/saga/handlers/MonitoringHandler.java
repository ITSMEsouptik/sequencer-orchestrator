package com.sequencer.orchestrator.saga.handlers;

import org.springframework.stereotype.Component;

import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;
import com.sequencer.orchestrator.saga.SagaResult;
import com.sequencer.orchestrator.saga.SagaStepHandler;

@Component
public class MonitoringHandler implements SagaStepHandler {

    @Override
    public EventType handlesEvent() {
        return EventType.CASE_CLOSED;
    }

    @Override
    public SagaResult handle(SequencerEvent event, TherapyOrder order) {
        return SagaResult.success(OrderStatus.CLOSED, null);
    }
}
