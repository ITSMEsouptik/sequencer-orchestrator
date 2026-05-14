package com.sequencer.orchestrator.domain.model.entity;

import com.sequencer.orchestrator.domain.model.base.AuditableEntity;
import jakarta.persistence.*;
import org.springframework.data.annotation.CreatedDate;

import java.time.OffsetDateTime;

@Entity
@Table(name = "processed_events")
@EntityListeners(AuditableEntity.class)
public class ProcessedEvent {
    @Id
    @Column(name = "event_id")
    private String eventId;

    @CreatedDate
    @Column(name = "processed_at", nullable = false)
    private OffsetDateTime processedAt;

    @Column(name = "expires_at", nullable = false)
    private OffsetDateTime expiresAt;
}
