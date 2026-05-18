package com.sequencer.orchestrator.api.dto;

import java.time.OffsetDateTime;

import com.sequencer.orchestrator.domain.model.enums.OrderStatus;

public record OrderStatusHistoryResponse(
    OrderStatus fromStatus,
    OrderStatus toStatus,
    OffsetDateTime changedAt
) {}
