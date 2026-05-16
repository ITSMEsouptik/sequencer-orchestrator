package com.sequencer.orchestrator.api.dto;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class CreateOrderRequest {
    @NotNull(message = "Patient ID required")
    private UUID patientId;

    @NotNull(message = "HCP ID is required")
    private UUID hcpID;

    @NotNull(message = "Treatment Center ID is required")
    private UUID treatmentCenterID;
}
