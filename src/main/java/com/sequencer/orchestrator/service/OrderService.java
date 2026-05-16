package com.sequencer.orchestrator.service;

import com.sequencer.orchestrator.api.dto.CreateOrderRequest;
import com.sequencer.orchestrator.api.dto.OrderSummaryResponse;
import com.sequencer.orchestrator.domain.model.entity.Patient;
import com.sequencer.orchestrator.domain.model.entity.TherapyOrder;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.domain.repository.PatientRepository;
import com.sequencer.orchestrator.domain.repository.TherapyOrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class OrderService {
    private final TherapyOrderRepository therapyOrderRepository;
    private final PatientRepository patientRepository;

    public OrderService(
            TherapyOrderRepository therapyOrderRepository,
            PatientRepository patientRepository
    ) {
        this.therapyOrderRepository = therapyOrderRepository;
        this.patientRepository = patientRepository;
    }

    @Transactional
    public TherapyOrder createOrder(CreateOrderRequest request) {
        Optional<Patient> patient = patientRepository.findById(request.getPatientId());

        if(patient.isEmpty()) {
            throw new IllegalArgumentException("Patient not found");
        }

        TherapyOrder order = TherapyOrder.builder()
                .patient(patient.get())
                .hcpID(request.getHcpID())
                .treatmentCenterID(request.getTreatmentCenterID())
                .build();

        therapyOrderRepository.save(order);
        return order;
    }

    @Transactional(readOnly = true)
    public List<OrderSummaryResponse> getAllOrders(OrderStatus status) {
        List<TherapyOrder> orders;
        if(status != null) {
            orders = therapyOrderRepository.findByStatus(status);
        }
        else {
            orders = therapyOrderRepository.findAll();
        }

        return orders.stream()
                .map(order -> new OrderSummaryResponse(
                        order.getId(),
                        order.getPatient().getName(),
                        order.getStatus(),
                        order.getCreatedAt(),
                        order.getUpdatedAt()
                ))
                .toList();
    }

    @Transactional(readOnly = true)
    public TherapyOrder getOrderByID(UUID id) {
        Optional<TherapyOrder> order = therapyOrderRepository.findById(id);
        if(order.isEmpty()) {
            throw new IllegalArgumentException("Order Not Found");
        }
        return order.get();
    }
}
