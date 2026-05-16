package com.sequencer.orchestrator;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

@EnableJpaAuditing
@SpringBootApplication
public class SequencerOrchestratorApplication {

    public static void main(String[] args) {
        SpringApplication.run(SequencerOrchestratorApplication.class, args);
    }

}
