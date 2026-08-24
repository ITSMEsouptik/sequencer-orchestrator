package com.sequencer.orchestrator.saga.handlers;

import org.springframework.stereotype.Component;

import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;
import com.sequencer.orchestrator.saga.SagaResult;
import com.sequencer.orchestrator.saga.SagaStepHandler;

@Component
public class OutboundShipmentReceivedHandler implements SagaStepHandler {

    @Override
    public EventType handlesEvent() {
        return EventType.OUTBOUND_SHIPMENT_RECEIVED;
    }

    @Override
    public SagaResult handle(SequencerEvent event, TherapyOrder order) {
        return SagaResult.success(OrderStatus.RECEIVED_AT_CENTER, EventType.INFUSION_SCHEDULED);
    }
}
