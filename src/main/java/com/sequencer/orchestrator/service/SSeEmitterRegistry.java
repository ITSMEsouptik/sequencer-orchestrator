package com.sequencer.orchestrator.service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class SSeEmitterRegistry {
    private final Map<UUID, SseEmitter> emitters = new ConcurrentHashMap<>();

    public SseEmitter add(UUID clientId) {
        SseEmitter emitter = new SseEmitter(0L);

        emitters.put(clientId, emitter);

        // auto remove when client disconnects or times out
        emitter.onCompletion(() -> emitters.remove(clientId));
        emitter.onTimeout(() -> emitters.remove(clientId));
        emitter.onError(e -> emitters.remove(clientId));

        return emitter;
    }

    public void remove(UUID clientId) {
        emitters.remove(clientId);
    }

    public void broadcast(Object data) {
        List<UUID> deadClients = new ArrayList<>();

        emitters.forEach((clientId, emitter) -> {
            try {
                emitter.send(SseEmitter.event().data(data));
            } catch (Exception e) {
                deadClients.add(clientId);
            }
        });

        deadClients.forEach(emitters::remove);
    }

}
