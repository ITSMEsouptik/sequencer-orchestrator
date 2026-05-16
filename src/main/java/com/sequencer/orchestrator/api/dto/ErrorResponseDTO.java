package com.sequencer.orchestrator.api.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.OffsetDateTime;

@Getter
@AllArgsConstructor
public class ErrorResponseDTO {
    private int status;
    private String message;
    private OffsetDateTime timestamp;
}
