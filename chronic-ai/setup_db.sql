-- ChronicAI Database Schema
-- A local-first telemedicine application for chronic patients and grassroots/district-level doctors in Vietnam
-- Run this in Supabase SQL Editor

-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM TYPES
-- ============================================

-- User roles
CREATE TYPE user_role AS ENUM ('patient', 'doctor', 'admin');

-- Gender
CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');

-- Blood types
CREATE TYPE blood_type AS ENUM ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown');

-- Smoking status
CREATE TYPE smoking_status AS ENUM ('never', 'former', 'current');

-- Alcohol consumption
CREATE TYPE alcohol_consumption AS ENUM ('none', 'occasional', 'moderate', 'heavy');

-- Exercise frequency
CREATE TYPE exercise_frequency AS ENUM ('none', 'light', 'moderate', 'regular');

-- Insurance coverage levels (Vietnamese BHYT)
CREATE TYPE insurance_level AS ENUM ('level_1', 'level_2', 'level_3', 'level_4');

-- Triage priority
CREATE TYPE triage_priority AS ENUM ('low', 'medium', 'high', 'urgent');

-- Profile status
CREATE TYPE profile_status AS ENUM ('active', 'inactive', 'deceased', 'suspended');

-- License status
CREATE TYPE license_status AS ENUM ('active', 'suspended', 'revoked', 'expired');

-- Healthcare facility types
CREATE TYPE facility_type AS ENUM (
    'commune_health_station', 
    'district_hospital', 
    'provincial_hospital', 
    'central_hospital', 
    'private_clinic'
);

-- Doctor verification status
CREATE TYPE verification_status AS ENUM ('pending', 'verified', 'rejected');

-- Doctor-patient relationship types
CREATE TYPE relationship_type AS ENUM ('primary_care', 'specialist', 'consultant');

-- Relationship status
CREATE TYPE assignment_status AS ENUM ('active', 'inactive', 'transferred');

-- Blood glucose timing
CREATE TYPE glucose_timing AS ENUM ('fasting', 'before_meal', 'after_meal', 'random');

-- Vital signs source
CREATE TYPE vital_source AS ENUM ('self_reported', 'clinic', 'hospital', 'device');

-- Medical record types
CREATE TYPE record_type AS ENUM ('prescription', 'lab', 'xray', 'ecg', 'notes', 'referral');

-- Consultation status
CREATE TYPE consultation_status AS ENUM ('triage', 'urgent', 'stable', 'resolved', 'cancelled');

-- Language preference
CREATE TYPE language_pref AS ENUM ('vi', 'en');

-- ============================================
-- TABLES
-- ============================================

-- --------------------------------------------
-- 1. Users (Authentication)
-- --------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    role user_role NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------
-- 2. Healthcare Facilities
-- --------------------------------------------
CREATE TABLE healthcare_facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type facility_type NOT NULL,
    address TEXT NOT NULL,
    ward VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    bed_count INTEGER,
    services TEXT[],
    operating_hours JSONB,
    emergency_available BOOLEAN DEFAULT false,
    coordinates POINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------
-- 3. Patients
-- --------------------------------------------
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Core Identity
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender gender_type NOT NULL,
    national_id VARCHAR(20),
    phone_primary VARCHAR(20) NOT NULL,
    phone_secondary VARCHAR(20),
    email VARCHAR(255),
    profile_photo_url VARCHAR(500),
    
    -- Address & Location
    address_street TEXT,
    address_ward VARCHAR(100) NOT NULL,
    address_district VARCHAR(100) NOT NULL,
    address_province VARCHAR(100) NOT NULL,
    location_coordinates POINT,
    
    -- Emergency Contact
    emergency_contact_name VARCHAR(255) NOT NULL,
    emergency_contact_phone VARCHAR(20) NOT NULL,
    emergency_contact_relationship VARCHAR(50) NOT NULL,
    
    -- Medical Demographics
    blood_type blood_type DEFAULT 'unknown',
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    bmi DECIMAL(4,2),
    
    -- Chronic Conditions (JSONB for flexibility)
    -- Structure: [{icd10_code, name, diagnosed_date, stage, notes}]
    chronic_conditions JSONB DEFAULT '[]',
    primary_diagnosis VARCHAR(20),
    diagnosis_date DATE,
    disease_stage VARCHAR(50),
    
    -- Current Medications
    -- Structure: [{name, dosage, frequency, timing, prescriber, start_date}]
    current_medications JSONB DEFAULT '[]',
    medication_adherence_score INTEGER CHECK (medication_adherence_score BETWEEN 1 AND 10),
    
    -- Medical History
    allergies TEXT[],
    -- Structure: [{procedure, date, facility, notes}]
    surgical_history JSONB DEFAULT '[]',
    -- Structure: {condition: [relatives]}
    family_medical_history JSONB DEFAULT '{}',
    smoking_status smoking_status,
    alcohol_consumption alcohol_consumption,
    exercise_frequency exercise_frequency,
    
    -- Insurance Information (Vietnamese BHYT)
    insurance_provider VARCHAR(100),
    insurance_number VARCHAR(50),
    insurance_expiry DATE,
    insurance_coverage_level insurance_level,
    
    -- App/System Fields
    preferred_language language_pref DEFAULT 'vi',
    -- Structure: {sms: bool, app: bool, reminders: {medication: bool, appointment: bool}}
    notification_preferences JSONB DEFAULT '{"sms": true, "app": true, "reminders": {"medication": true, "appointment": true}}',
    assigned_doctor_id UUID,
    last_checkup_date DATE,
    next_appointment_date TIMESTAMPTZ,
    triage_priority triage_priority DEFAULT 'low',
    profile_status profile_status DEFAULT 'active',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_patient_user UNIQUE (user_id)
);

-- --------------------------------------------
-- 4. Doctors
-- --------------------------------------------
CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Core Identity
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender gender_type NOT NULL,
    national_id VARCHAR(20) NOT NULL,
    phone_primary VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    profile_photo_url VARCHAR(500),
    
    -- Professional Credentials
    medical_license_number VARCHAR(50) NOT NULL UNIQUE,
    license_issue_date DATE NOT NULL,
    license_expiry_date DATE,
    license_status license_status DEFAULT 'active',
    medical_degree VARCHAR(100) NOT NULL,
    graduation_year INTEGER NOT NULL,
    medical_school VARCHAR(255) NOT NULL,
    
    -- Specializations
    primary_specialty VARCHAR(100) NOT NULL,
    secondary_specialties TEXT[],
    -- Structure: [{specialty, certifying_body, certificate_number, issue_date, expiry_date}]
    specialty_certifications JSONB DEFAULT '[]',
    years_of_experience INTEGER NOT NULL,
    
    -- Work Information
    healthcare_facility_id UUID REFERENCES healthcare_facilities(id),
    healthcare_facility_name VARCHAR(255) NOT NULL,
    facility_type facility_type NOT NULL,
    position_title VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    work_address TEXT,
    work_phone VARCHAR(20),
    
    -- Availability
    -- Structure: {day: {start, end, break_start, break_end}}
    consultation_hours JSONB,
    max_daily_consultations INTEGER,
    average_consultation_duration INTEGER,
    accepts_new_patients BOOLEAN DEFAULT true,
    teleconsultation_enabled BOOLEAN DEFAULT true,
    
    -- Chronic Disease Focus
    chronic_disease_focus TEXT[],
    -- Structure: {condition: {years, patients_managed, certifications}}
    chronic_management_experience JSONB DEFAULT '{}',
    
    -- Statistics & Ratings
    total_consultations INTEGER DEFAULT 0,
    active_patient_count INTEGER DEFAULT 0,
    average_rating DECIMAL(3,2),
    total_ratings INTEGER DEFAULT 0,
    response_time_avg_hours DECIMAL(5,2),
    
    -- App/System Fields
    preferred_language language_pref DEFAULT 'vi',
    notification_preferences JSONB DEFAULT '{"sms": true, "app": true, "urgent_notifications": true}',
    verification_status verification_status DEFAULT 'pending',
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES users(id),
    profile_status profile_status DEFAULT 'active',
    bio TEXT,
    languages_spoken TEXT[] DEFAULT ARRAY['vi'],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_doctor_user UNIQUE (user_id)
);

-- Add FK from patients to doctors for assigned_doctor_id
ALTER TABLE patients 
ADD CONSTRAINT fk_assigned_doctor 
FOREIGN KEY (assigned_doctor_id) REFERENCES doctors(id) ON DELETE SET NULL;

-- --------------------------------------------
-- 5. Doctor-Patient Assignments
-- --------------------------------------------
CREATE TABLE doctor_patient_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    assigned_date DATE NOT NULL DEFAULT CURRENT_DATE,
    assigned_by UUID REFERENCES users(id),
    status assignment_status DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_doctor_patient UNIQUE (doctor_id, patient_id)
);

-- --------------------------------------------
-- 6. Vital Signs Log
-- --------------------------------------------
CREATE TABLE vital_signs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID REFERENCES users(id),
    
    -- Measurements
    blood_pressure_systolic INTEGER CHECK (blood_pressure_systolic BETWEEN 50 AND 300),
    blood_pressure_diastolic INTEGER CHECK (blood_pressure_diastolic BETWEEN 30 AND 200),
    heart_rate INTEGER CHECK (heart_rate BETWEEN 30 AND 250),
    blood_glucose DECIMAL(5,2) CHECK (blood_glucose BETWEEN 1.0 AND 50.0),
    blood_glucose_timing glucose_timing,
    temperature DECIMAL(4,2) CHECK (temperature BETWEEN 30.0 AND 45.0),
    oxygen_saturation INTEGER CHECK (oxygen_saturation BETWEEN 50 AND 100),
    weight_kg DECIMAL(5,2) CHECK (weight_kg BETWEEN 1.0 AND 500.0),
    
    notes TEXT,
    source vital_source DEFAULT 'self_reported',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------
-- 7. Medical Records
-- --------------------------------------------
CREATE TABLE medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id),
    record_type record_type NOT NULL,
    title VARCHAR(255),
    content_text TEXT,
    image_path VARCHAR(500),
    -- Structure: {diagnosis, findings, recommendations, confidence_score}
    analysis_result JSONB,
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES doctors(id),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------
-- 8. Record Embeddings (for RAG)
-- --------------------------------------------
CREATE TABLE record_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id UUID REFERENCES medical_records(id) ON DELETE CASCADE,
    chunk_content TEXT NOT NULL,
    embedding vector(768),  -- 768 dimensions for nomic-embed-text
    chunk_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- --------------------------------------------
-- 9. Consultations
-- --------------------------------------------
CREATE TABLE consultations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id),
    
    -- Consultation details
    chief_complaint TEXT,
    -- Structure: [{role, content, timestamp, attachments}]
    messages JSONB DEFAULT '[]',
    summary TEXT,
    -- Structure: {diagnosis, medications, follow_up, referrals}
    clinical_notes JSONB DEFAULT '{}',
    
    status consultation_status DEFAULT 'triage',
    priority triage_priority DEFAULT 'medium',
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_minutes INTEGER,
    
    -- Follow-up
    follow_up_required BOOLEAN DEFAULT false,
    follow_up_date DATE,
    follow_up_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Users
CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_role ON users(role);

-- Patients
CREATE INDEX idx_patients_user_id ON patients(user_id);
CREATE INDEX idx_patients_assigned_doctor ON patients(assigned_doctor_id);
CREATE INDEX idx_patients_province ON patients(address_province);
CREATE INDEX idx_patients_district ON patients(address_district);
CREATE INDEX idx_patients_status ON patients(profile_status);
CREATE INDEX idx_patients_triage ON patients(triage_priority);

-- Doctors
CREATE INDEX idx_doctors_user_id ON doctors(user_id);
CREATE INDEX idx_doctors_facility ON doctors(healthcare_facility_id);
CREATE INDEX idx_doctors_specialty ON doctors(primary_specialty);
CREATE INDEX idx_doctors_verification ON doctors(verification_status);
CREATE INDEX idx_doctors_license ON doctors(medical_license_number);

-- Healthcare Facilities
CREATE INDEX idx_facilities_province ON healthcare_facilities(province);
CREATE INDEX idx_facilities_district ON healthcare_facilities(district);
CREATE INDEX idx_facilities_type ON healthcare_facilities(type);

-- Doctor-Patient Assignments
CREATE INDEX idx_assignments_doctor ON doctor_patient_assignments(doctor_id);
CREATE INDEX idx_assignments_patient ON doctor_patient_assignments(patient_id);
CREATE INDEX idx_assignments_status ON doctor_patient_assignments(status);

-- Vital Signs
CREATE INDEX idx_vitals_patient ON vital_signs(patient_id);
CREATE INDEX idx_vitals_recorded_at ON vital_signs(recorded_at DESC);

-- Medical Records
CREATE INDEX idx_records_patient ON medical_records(patient_id);
CREATE INDEX idx_records_doctor ON medical_records(doctor_id);
CREATE INDEX idx_records_type ON medical_records(record_type);
CREATE INDEX idx_records_created ON medical_records(created_at DESC);

-- Record Embeddings (vector similarity search)
CREATE INDEX idx_embeddings_record ON record_embeddings(record_id);
CREATE INDEX ON record_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Consultations
CREATE INDEX idx_consultations_patient ON consultations(patient_id);
CREATE INDEX idx_consultations_doctor ON consultations(doctor_id);
CREATE INDEX idx_consultations_status ON consultations(status);
CREATE INDEX idx_consultations_created ON consultations(created_at DESC);

-- ============================================
-- TRIGGERS FOR updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_doctors_updated_at BEFORE UPDATE ON doctors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facilities_updated_at BEFORE UPDATE ON healthcare_facilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_records_updated_at BEFORE UPDATE ON medical_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_consultations_updated_at BEFORE UPDATE ON consultations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE users IS 'Authentication table for all user types';
COMMENT ON TABLE patients IS 'Patient profiles with chronic disease management focus';
COMMENT ON TABLE doctors IS 'Doctor profiles with credentials and specialization info';
COMMENT ON TABLE healthcare_facilities IS 'Vietnamese healthcare facilities from commune to central level';
COMMENT ON TABLE doctor_patient_assignments IS 'Many-to-many relationships between doctors and patients';
COMMENT ON TABLE vital_signs IS 'Patient vital signs log for health monitoring';
COMMENT ON TABLE medical_records IS 'Medical documents including prescriptions, lab results, imaging';
COMMENT ON TABLE record_embeddings IS 'Vector embeddings for RAG-based medical record search';
COMMENT ON TABLE consultations IS 'Telemedicine consultation sessions';
