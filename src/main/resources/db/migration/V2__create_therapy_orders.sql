CREATE TABLE therapy_orders (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id            UUID         NOT NULL REFERENCES patients (id),
    hcp_id                UUID         NOT NULL,
    treatment_center_id   UUID         NOT NULL,
    status                VARCHAR(50)  NOT NULL,
    manufacturing_slot_date DATE,
    apheresis_date          DATE,
    infusion_target_date    DATE,
    failure_reason          TEXT,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_therapy_orders_status     ON therapy_orders (status);
CREATE INDEX idx_therapy_orders_patient_id ON therapy_orders (patient_id);
