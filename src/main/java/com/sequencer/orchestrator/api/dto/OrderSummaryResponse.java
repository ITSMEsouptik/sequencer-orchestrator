package com.sequencer.orchestrator.api.dto;

import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class OrderSummaryResponse {
    private UUID orderId;
    private String patientName;
    private OrderStatus status;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
