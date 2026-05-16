package com.sequencer.orchestrator.domain.model.entity;

import jakarta.persistence.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.OffsetDateTime;

@Entity
@Table(name = "processed_events")
public class ProcessedEvent {
    @Id
    @Column(name = "event_id")
    private String eventId;

    @Column(name = "processed_at", nullable = false)
    private OffsetDateTime processedAt;

    @Column(name = "expires_at", nullable = false)
    private OffsetDateTime expiresAt;
}
