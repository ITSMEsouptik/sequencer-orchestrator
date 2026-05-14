CREATE TABLE patients (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    date_of_birth       DATE         NOT NULL,
    diagnosis_code      VARCHAR(50)  NOT NULL,
    hcp_id              UUID         NOT NULL,
    treatment_center_id UUID         NOT NULL,
    enrollment_date     DATE         NOT NULL DEFAULT CURRENT_DATE,
    status              VARCHAR(50)  NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patients_status ON patients (status);
