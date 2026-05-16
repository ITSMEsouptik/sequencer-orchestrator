package com.sequencer.orchestrator.domain.model.entity;

import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.domain.model.base.AuditableEntity;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name="therapy_orders")
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Getter
public class TherapyOrder extends AuditableEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;

    @Column(name="hcp_id", nullable = false)
    private UUID hcpID;

    @Column(name = "treatment_center_id", nullable = false, updatable = false)
    private UUID treatmentCenterID;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    @Builder.Default
    private OrderStatus status = OrderStatus.ENROLLED;

    @Column(name = "manufacturing_slot_date")
    private LocalDate manufacturingSlotDate;

    @Column(name = "apheresis_date")
    private LocalDate apheresisDate;

    @Column(name = "infusion_target_date")
    private LocalDate infusionTargetDate;

    @Column(name = "failure_reason")
    private String failureReason;
}
