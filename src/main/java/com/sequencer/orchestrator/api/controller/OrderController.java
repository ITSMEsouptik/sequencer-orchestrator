package com.sequencer.orchestrator.api.controller;

import com.sequencer.orchestrator.api.dto.CreateOrderRequest;
import com.sequencer.orchestrator.api.dto.OrderStatusHistoryResponse;
import com.sequencer.orchestrator.api.dto.OrderSummaryResponse;
import com.sequencer.orchestrator.domain.model.enums.OrderStatus;
import com.sequencer.orchestrator.service.OrderService;
import com.sequencer.orchestrator.service.SSeEmitterRegistry;

import jakarta.validation.Valid;

import org.springframework.http.MediaType;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("api/orders")
public class OrderController {
    private final OrderService orderService;
    private final SSeEmitterRegistry sseEmitterRegistry;

    public OrderController(OrderService orderService,
        SSeEmitterRegistry sseEmitterRegistry
    ) {
        this.orderService = orderService;
        this.sseEmitterRegistry = sseEmitterRegistry;
    }

    @PostMapping
    public ResponseEntity<OrderSummaryResponse> createOrder(
            @RequestBody
            @Valid
            CreateOrderRequest request
    ){
        OrderSummaryResponse order = orderService.createOrder(request);
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(order);
    }

    @GetMapping
    public ResponseEntity<List<OrderSummaryResponse>> getOrders(
        @RequestParam(required = false) OrderStatus status
    ){
        List<OrderSummaryResponse> orders = orderService.getAllOrders(status);
        return ResponseEntity.status(HttpStatus.OK)
                .body(orders);
    }

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamOrders() {
        UUID clientId = UUID.randomUUID();
        return sseEmitterRegistry.add(clientId);
    }

    @GetMapping("/{id}")
    public ResponseEntity<OrderSummaryResponse> getOrder(
            @PathVariable UUID id
            ) {
        OrderSummaryResponse order = orderService.getOrderByID(id);
        return ResponseEntity.status(HttpStatus.OK)
                .body(order);
    }

    @GetMapping("/{id}/history")
    public ResponseEntity<List<OrderStatusHistoryResponse>> getHistory(
        @PathVariable UUID id
    ){
        List<OrderStatusHistoryResponse> history = orderService.getStatusHistory(id);
        return ResponseEntity.status(HttpStatus.OK)
        .body(history);
    }
}
