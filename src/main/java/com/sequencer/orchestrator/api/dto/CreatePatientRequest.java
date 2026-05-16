package com.sequencer.orchestrator.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class CreatePatientRequest {
    @NotBlank(message = "Name is required")
    private String name;

    @NotNull(message = "Date of birth is required")
    private LocalDate dateOfBirth;

    @NotBlank(message = "Diagnosis code is required")
    private String diagnosisCode;

    @NotNull(message = "HCP ID is required")
    private UUID hcpID;

    @NotNull(message = "Treatment Center ID is required")
    private UUID treatmentCenterID;
}
