package com.sequencer.orchestrator.service;

import java.time.OffsetDateTime;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.sequencer.orchestrator.domain.model.entity.ProcessedEvent;
import com.sequencer.orchestrator.domain.repository.ProcessedEventRepository;

@Service
public class IdempotencyService {

    private final ProcessedEventRepository processedEventRepository;
    private final long ttlHours;

    public IdempotencyService(
        ProcessedEventRepository processedEventRepository,
        @Value("${sequencer.idempotency.ttl-hours}") long ttlHours
    ) {
        this.processedEventRepository = processedEventRepository;
        this.ttlHours = ttlHours;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean isAlreadyProcessed(String eventId) {
        boolean exist = processedEventRepository.existsById(eventId);
        if(!exist) {
            ProcessedEvent event = ProcessedEvent.builder()
            .eventId(eventId)
            .processedAt(OffsetDateTime.now())
            .expiresAt(OffsetDateTime.now().plusHours(ttlHours))
            .build();

            processedEventRepository.save(event);
        }
        return exist;
    }
}
