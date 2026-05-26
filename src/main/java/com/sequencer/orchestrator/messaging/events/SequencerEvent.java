package com.sequencer.orchestrator.messaging.events;

import com.sequencer.orchestrator.domain.model.enums.AggregatedType;
import com.sequencer.orchestrator.domain.model.enums.EventType;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class SequencerEvent {
    private String eventId;         // idempotency key
    private EventType eventType;       // routes to the right handler
    private String aggregatedId;    // the order UUID
    private AggregatedType aggregatedType;  // THERAPY_ORDER
    private String orderId;
    private String patientId;
    private String status;
    private String timestamp;
}
