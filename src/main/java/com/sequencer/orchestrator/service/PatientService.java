package com.sequencer.orchestrator.service;

import com.sequencer.orchestrator.api.dto.CreatePatientRequest;
import com.sequencer.orchestrator.domain.model.entity.Patient;
import com.sequencer.orchestrator.domain.repository.PatientRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PatientService {
    private final PatientRepository patientRepository;

    public PatientService(PatientRepository patientRepository){
        this.patientRepository = patientRepository;
    }

    @Transactional
    public Patient enrollPatient(CreatePatientRequest request) {
        boolean exists = patientRepository.existsByNameAndDateOfBirth(
                request.getName(),
                request.getDateOfBirth()
        );
        if (exists) {
           throw new IllegalArgumentException("Patient already exist with this name and date of birth");
        }

        Patient patient = Patient.
                builder().
                name(request.getName())
                .dateOfBirth(request.getDateOfBirth())
                .diagnosisCode(request.getDiagnosisCode())
                .hcpID(request.getHcpID())
                .treatmentCenterID(request.getTreatmentCenterID())
                .build();
        patientRepository.save(patient);
        return patient;
    }
}
