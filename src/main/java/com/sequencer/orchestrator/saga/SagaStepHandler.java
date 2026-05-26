package com.sequencer.orchestrator.saga;

import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.EventType;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;

public interface SagaStepHandler {
    EventType handlesEvent();
    SagaResult handle(SequencerEvent event, TherapyOrder order);
}
