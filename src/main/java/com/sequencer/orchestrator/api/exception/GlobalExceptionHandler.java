package com.sequencer.orchestrator.api.exception;

import com.sequencer.orchestrator.api.dto.ErrorResponseDTO;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidation(
            MethodArgumentNotValidException ex
    ) {
        String message = ex.getBindingResult().
                getFieldErrors().
                stream().
                map(e -> e.getField() +
                        ": " +
                        e.getDefaultMessage()
                ).
                collect(Collectors.joining(", "));
        ErrorResponseDTO err = new ErrorResponseDTO(
                400,
                message,
                OffsetDateTime.now()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).
                body(err);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponseDTO> handleTypeMismatch(
            MethodArgumentTypeMismatchException ex
    ){
        String message;
        var requiredType = ex.getRequiredType();
        if(requiredType != null && requiredType.isEnum()) {
            String accepted = Arrays.stream(requiredType.getEnumConstants())
                    .map(Object::toString)
                    .collect(Collectors.joining(", "));
            message = "Invalid value " + ex.getValue() +
                    " for parameter " + ex.getName() +
                    ". Accepted values: " +
                    accepted;
        }
        else {
            message = "Invalid value " + ex.getValue() +
                    " for parameter " + ex.getName() +
                    ". Expected type: " + (
                            requiredType != null ? requiredType.getSimpleName()
                                    : "unknown"
                    );
        }
        ErrorResponseDTO error = new ErrorResponseDTO(
                400,
                message,
                OffsetDateTime.now()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(error);
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotFound(
            RuntimeException ex
    ){
        ErrorResponseDTO error = new ErrorResponseDTO(
                404,
                ex.getMessage(),
                OffsetDateTime.now()
        );
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(error);
    }
}
