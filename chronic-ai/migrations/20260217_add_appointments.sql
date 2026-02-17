-- Add appointment booking workflow for patient/doctor calendar.

DO $$
BEGIN
    CREATE TYPE appointment_status AS ENUM (
        'pending',
        'accepted',
        'rejected',
        'cancelled',
        'completed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE appointment_contact_method AS ENUM (
        'phone',
        'sms',
        'app'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duration_minutes BETWEEN 10 AND 240),
    status appointment_status NOT NULL DEFAULT 'pending',
    appointment_type VARCHAR(50) NOT NULL DEFAULT 'follow_up',
    chief_complaint TEXT NOT NULL,
    symptoms TEXT,
    notes TEXT,
    contact_phone VARCHAR(20),
    preferred_contact_method appointment_contact_method NOT NULL DEFAULT 'phone',
    is_follow_up BOOLEAN NOT NULL DEFAULT true,
    doctor_response_note TEXT,
    rejection_reason TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT appointments_time_order CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_start_at ON appointments(start_at);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

DROP TRIGGER IF EXISTS update_appointments_updated_at ON appointments;
CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
