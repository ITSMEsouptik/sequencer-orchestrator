package com.sequencer.orchestrator.service;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sequencer.orchestrator.domain.model.entity.OutboxEvent;
import com.sequencer.orchestrator.domain.repository.OutboxEventRepository;
import com.sequencer.orchestrator.messaging.events.SequencerEvent;

import io.awspring.cloud.sns.core.SnsTemplate;

@Service
public class OutboxProcessorService {

    private static final Logger log = LoggerFactory.getLogger(OutboxProcessorService.class);
    private final OutboxEventRepository outboxEventRepository;
    private final SnsTemplate snsTemplate;
    private final ObjectMapper objectMapper;
    private final String topicArn;

    public OutboxProcessorService(
            OutboxEventRepository outboxEventRepository,
            SnsTemplate snsTemplate,
            ObjectMapper objectMapper,
            @Value("${sequencer.sns.topic-arn}") String topicArn) {
        this.outboxEventRepository = outboxEventRepository;
        this.snsTemplate = snsTemplate;
        this.objectMapper = objectMapper;
        this.topicArn = topicArn;
    }

    @Scheduled(fixedDelay = 1000)
    @Transactional
    public void processOutbox() {
        List<OutboxEvent> events = outboxEventRepository.findTop50ByPublishedFalseOrderByCreatedAtAsc();
        for (OutboxEvent event : events) {
            try {
                SequencerEvent sequencerEvent = toSequencerEvent(event);
                String payload = objectMapper.writeValueAsString(sequencerEvent);
                // eventType header is required: SNS filter policies inspect message attributes,
                // not the message body. Omitting it causes silent message loss on vendor queues.
                snsTemplate.send(topicArn,
                        MessageBuilder.withPayload(payload)
                                .setHeader("eventType", event.getEventType().name())
                                .build());
                log.info("Published event {} for aggregate {} to SNS", event.getEventType(), event.getAggregatedID());
                event.setPublished();
            } catch (Exception e) {
                log.error("Failed to publish outbox event {} for aggregate {}: {}",
                        event.getEventType(), event.getAggregatedID(), e.getMessage(), e);
            }
        }
    }

    private SequencerEvent toSequencerEvent(OutboxEvent outboxEvent) {
        JsonNode p = outboxEvent.getPayload();
        return new SequencerEvent(
                p.get("eventId").asText(),
                outboxEvent.getEventType(),
                outboxEvent.getAggregatedID().toString(),
                outboxEvent.getAggregatedType(),
                p.get("orderId").asText(),
                p.get("patientId").asText(),
                p.get("status").asText(),
                p.get("timestamp").asText()
        );
    }
}
