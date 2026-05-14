package com.sequencer.orchestrator.domain.repository;

import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface TherapyOrderRepository extends JpaRepository<TherapyOrder, UUID> {
    List<TherapyOrder> findByStatus(OrderStatus status);
    List<TherapyOrder> findByPatientId(UUID patientID);
    List<TherapyOrder> findByStatusNotIn(List<OrderStatus> statuses);
}
