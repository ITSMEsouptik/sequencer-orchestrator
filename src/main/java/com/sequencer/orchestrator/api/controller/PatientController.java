package com.sequencer.orchestrator.api.controller;

import com.sequencer.orchestrator.api.dto.CreatePatientRequest;
import com.sequencer.orchestrator.domain.model.entity.Patient;
import com.sequencer.orchestrator.service.PatientService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("api/patients")
public class PatientController {
    private final PatientService patientService;

    public PatientController(PatientService patientService) {
        this.patientService = patientService;
    }

    @PostMapping
    public ResponseEntity<Patient> enrollPatient(
            @RequestBody
            @Valid
            CreatePatientRequest request
    ){
        Patient patient = patientService.enrollPatient(request);
        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(patient);
    }
}
