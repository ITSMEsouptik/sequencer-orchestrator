package com.sequencer.orchestrator.domain.model.base;

import jakarta.persistence.*;
import lombok.Getter;
import org.hibernate.annotations.UuidGenerator;
import java.util.UUID;

@MappedSuperclass
@Getter
public abstract class BaseEntity {
    @Id
    @GeneratedValue
    @UuidGenerator
    private UUID id;
}
