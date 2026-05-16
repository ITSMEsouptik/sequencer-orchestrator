package com.sequencer.orchestrator.domain.model.entity;

import com.sequencer.orchestrator.domain.model.enums.PatientStatus;
import com.sequencer.orchestrator.domain.model.base.AuditableEntity;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "patients")
@Builder
@Getter
@NoArgsConstructor
@AllArgsConstructor
public class Patient extends AuditableEntity {

    @Column(name = "name", nullable = false, length = 255)
    private String name;

    @Column(name = "date_of_birth", nullable = false)
    private LocalDate dateOfBirth;

    @Column(name = "diagnosis_code", nullable = false, length = 50)
    private String diagnosisCode;

    @Column(name = "hcp_id", nullable = false, updatable = false)
    private UUID hcpID;

    @Column(name = "treatment_center_id", nullable = false, updatable = false)
    private UUID treatmentCenterID;

    @Column(name = "enrollment_date", nullable = false)
    @Builder.Default
    private LocalDate enrollmentDate = LocalDate.now();

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    @Builder.Default
    private PatientStatus status = PatientStatus.REFERRED;
}
