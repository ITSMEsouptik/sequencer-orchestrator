package com.sequencer.orchestrator.domain.repository;

import com.sequencer.orchestrator.domain.model.entity.Patient;
import com.sequencer.orchestrator.domain.model.enums.PatientStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Repository
public interface PatientRepository extends JpaRepository<Patient, UUID> {
    List<Patient> findByStatus(PatientStatus status);
    List<Patient> findByHcpID(UUID hcpID);
    boolean existsByNameAndDateOfBirth(String name, LocalDate dateOfBirth);
}
