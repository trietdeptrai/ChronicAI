# ChronicAI Data Model Definitions

This document defines the comprehensive data fields for users (patients and doctors) in the ChronicAI telemedicine application, designed for chronic disease management in Vietnam's grassroots/district healthcare system.

---

## Table of Contents
1. [Patient Profile](#patient-profile)
2. [Doctor Profile](#doctor-profile)
3. [Shared Authentication](#shared-authentication)
4. [Patient-Doctor Relationships](#patient-doctor-relationships)
5. [Additional Tables](#additional-tables)

---

## 1. Patient Profile

### Core Identity
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `user_id` | UUID | Yes | FK to authentication table |
| `full_name` | VARCHAR(255) | Yes | Full legal name |
| `date_of_birth` | DATE | Yes | Birth date for age calculation |
| `gender` | ENUM | Yes | `male`, `female`, `other` |
| `national_id` | VARCHAR(20) | No | CCCD/CMND number (Vietnamese ID) |
| `phone_primary` | VARCHAR(20) | Yes | Primary contact number |
| `phone_secondary` | VARCHAR(20) | No | Backup contact number |
| `email` | VARCHAR(255) | No | Email address (optional for elderly) |

### Address & Location
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address_street` | TEXT | No | Street address |
| `address_ward` | VARCHAR(100) | Yes | Phường/Xã (Ward/Commune) |
| `address_district` | VARCHAR(100) | Yes | Quận/Huyện (District) |
| `address_province` | VARCHAR(100) | Yes | Tỉnh/Thành phố (Province/City) |
| `location_coordinates` | POINT | No | GPS coordinates for remote areas |

### Emergency Contact
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `emergency_contact_name` | VARCHAR(255) | Yes | Name of emergency contact |
| `emergency_contact_phone` | VARCHAR(20) | Yes | Emergency contact phone |
| `emergency_contact_relationship` | VARCHAR(50) | Yes | Relationship (spouse, child, etc.) |

### Medical Demographics
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `blood_type` | ENUM | No | `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`, `unknown` |
| `height_cm` | DECIMAL(5,2) | No | Height in centimeters |
| `weight_kg` | DECIMAL(5,2) | No | Current weight in kilograms |
| `bmi` | DECIMAL(4,2) | No | Calculated BMI |

### Chronic Conditions
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chronic_conditions` | JSONB | Yes | Array of chronic conditions with details |
| `primary_diagnosis` | VARCHAR(20) | No | ICD-10 code of primary condition |
| `diagnosis_date` | DATE | No | Date of initial diagnosis |
| `disease_stage` | VARCHAR(50) | No | Stage/severity of primary condition |

**Example `chronic_conditions` structure:**
```json
[
  {
    "icd10_code": "E11",
    "name": "Type 2 Diabetes",
    "diagnosed_date": "2020-03-15",
    "stage": "controlled",
    "notes": "On metformin 500mg"
  },
  {
    "icd10_code": "I10",
    "name": "Essential Hypertension",
    "diagnosed_date": "2019-08-22",
    "stage": "stage_2",
    "notes": "Morning BP typically 150/90"
  }
]
```

### Current Medications
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_medications` | JSONB | No | List of current medications |
| `medication_adherence_score` | INTEGER | No | Self-reported adherence (1-10) |

**Example `current_medications` structure:**
```json
[
  {
    "name": "Metformin",
    "dosage": "500mg",
    "frequency": "2x daily",
    "timing": "after meals",
    "prescriber": "Dr. Nguyễn Văn A",
    "start_date": "2020-04-01"
  }
]
```

### Medical History
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `allergies` | TEXT[] | No | List of known allergies |
| `surgical_history` | JSONB | No | Past surgeries with dates |
| `family_medical_history` | JSONB | No | Relevant family conditions |
| `smoking_status` | ENUM | No | `never`, `former`, `current` |
| `alcohol_consumption` | ENUM | No | `none`, `occasional`, `moderate`, `heavy` |
| `exercise_frequency` | ENUM | No | `none`, `light`, `moderate`, `regular` |

### Insurance Information
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `insurance_provider` | VARCHAR(100) | No | BHYT (health insurance) provider |
| `insurance_number` | VARCHAR(50) | No | Insurance card number |
| `insurance_expiry` | DATE | No | Insurance expiration date |
| `insurance_coverage_level` | ENUM | No | `level_1`, `level_2`, `level_3`, `level_4` |

### App/System Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `preferred_language` | ENUM | Yes | `vi`, `en` (default: `vi`) |
| `notification_preferences` | JSONB | No | SMS, app, reminder settings |
| `assigned_doctor_id` | UUID | No | FK to primary care doctor |
| `last_checkup_date` | DATE | No | Last in-person checkup |
| `next_appointment_date` | TIMESTAMPTZ | No | Scheduled next appointment |
| `triage_priority` | ENUM | No | `low`, `medium`, `high`, `urgent` |
| `profile_status` | ENUM | Yes | `active`, `inactive`, `deceased` |
| `created_at` | TIMESTAMPTZ | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | Yes | Last update timestamp |

---

## 2. Doctor Profile

### Core Identity
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `user_id` | UUID | Yes | FK to authentication table |
| `full_name` | VARCHAR(255) | Yes | Full legal name |
| `date_of_birth` | DATE | Yes | Birth date |
| `gender` | ENUM | Yes | `male`, `female`, `other` |
| `national_id` | VARCHAR(20) | Yes | CCCD/CMND number |
| `phone_primary` | VARCHAR(20) | Yes | Primary contact number |
| `email` | VARCHAR(255) | Yes | Professional email |
| `profile_photo_url` | VARCHAR(500) | No | URL to profile photo |

### Professional Credentials
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `medical_license_number` | VARCHAR(50) | Yes | Ministry of Health license number |
| `license_issue_date` | DATE | Yes | When license was issued |
| `license_expiry_date` | DATE | No | License expiration (if applicable) |
| `license_status` | ENUM | Yes | `active`, `suspended`, `revoked`, `expired` |
| `medical_degree` | VARCHAR(100) | Yes | Highest medical degree |
| `graduation_year` | INTEGER | Yes | Year of graduation |
| `medical_school` | VARCHAR(255) | Yes | Name of medical institution |

### Specializations
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `primary_specialty` | VARCHAR(100) | Yes | Primary medical specialty |
| `secondary_specialties` | TEXT[] | No | Additional specialties |
| `specialty_certifications` | JSONB | No | Specialty board certifications |
| `years_of_experience` | INTEGER | Yes | Total years practicing |

**Example `specialty_certifications` structure:**
```json
[
  {
    "specialty": "Internal Medicine",
    "certifying_body": "Vietnam Medical Association",
    "certificate_number": "NB-12345",
    "issue_date": "2015-06-20",
    "expiry_date": "2025-06-20"
  }
]
```

### Work Information
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `healthcare_facility_id` | UUID | Yes | FK to healthcare facilities table |
| `healthcare_facility_name` | VARCHAR(255) | Yes | Name of facility |
| `facility_type` | ENUM | Yes | `commune_health_station`, `district_hospital`, `provincial_hospital`, `central_hospital`, `private_clinic` |
| `position_title` | VARCHAR(100) | Yes | Job title/position |
| `department` | VARCHAR(100) | No | Department within facility |
| `work_address` | TEXT | No | Work address |
| `work_phone` | VARCHAR(20) | No | Office phone number |

### Availability
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `consultation_hours` | JSONB | No | Available consultation times |
| `max_daily_consultations` | INTEGER | No | Maximum patients per day |
| `average_consultation_duration` | INTEGER | No | Typical consult length (minutes) |
| `accepts_new_patients` | BOOLEAN | Yes | Currently accepting new patients |
| `teleconsultation_enabled` | BOOLEAN | Yes | Available for remote consults |

**Example `consultation_hours` structure:**
```json
{
  "monday": {"start": "08:00", "end": "17:00", "break_start": "12:00", "break_end": "13:30"},
  "tuesday": {"start": "08:00", "end": "17:00", "break_start": "12:00", "break_end": "13:30"},
  "wednesday": {"start": "08:00", "end": "12:00"}
}
```

### Chronic Disease Focus
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chronic_disease_focus` | TEXT[] | No | ICD-10 codes of focus areas |
| `chronic_management_experience` | JSONB | No | Experience with specific conditions |

**Example `chronic_management_experience` structure:**
```json
{
  "diabetes": {"years": 8, "patients_managed": 150, "certifications": ["Diabetes Educator 2020"]},
  "hypertension": {"years": 10, "patients_managed": 300}
}
```

### Statistics & Ratings
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `total_consultations` | INTEGER | No | Total consultations completed |
| `active_patient_count` | INTEGER | No | Current active patients |
| `average_rating` | DECIMAL(3,2) | No | Patient rating (1-5) |
| `total_ratings` | INTEGER | No | Number of ratings received |
| `response_time_avg_hours` | DECIMAL(5,2) | No | Average response time |

### App/System Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `preferred_language` | ENUM | Yes | `vi`, `en` (default: `vi`) |
| `notification_preferences` | JSONB | No | Alert/notification settings |
| `verification_status` | ENUM | Yes | `pending`, `verified`, `rejected` |
| `verified_at` | TIMESTAMPTZ | No | When credentials were verified |
| `verified_by` | UUID | No | Admin who verified |
| `profile_status` | ENUM | Yes | `active`, `inactive`, `suspended` |
| `bio` | TEXT | No | Professional biography |
| `languages_spoken` | TEXT[] | No | Languages doctor speaks |
| `created_at` | TIMESTAMPTZ | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | Yes | Last update timestamp |

---

## 3. Shared Authentication

### Users Table (Authentication)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `phone_number` | VARCHAR(20) | Yes | Phone for OTP login |
| `email` | VARCHAR(255) | No | Email (optional) |
| `password_hash` | VARCHAR(255) | No | Hashed password (if not OTP-only) |
| `role` | ENUM | Yes | `patient`, `doctor`, `admin` |
| `is_active` | BOOLEAN | Yes | Account active status |
| `is_verified` | BOOLEAN | Yes | Phone/identity verified |
| `last_login` | TIMESTAMPTZ | No | Last login timestamp |
| `login_count` | INTEGER | No | Total login count |
| `failed_login_attempts` | INTEGER | No | Failed attempts counter |
| `locked_until` | TIMESTAMPTZ | No | Account lock expiration |
| `created_at` | TIMESTAMPTZ | Yes | Account creation |
| `updated_at` | TIMESTAMPTZ | Yes | Last update |

---

## 4. Patient-Doctor Relationships

### Doctor-Patient Assignments
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `doctor_id` | UUID | Yes | FK to doctors table |
| `patient_id` | UUID | Yes | FK to patients table |
| `relationship_type` | ENUM | Yes | `primary_care`, `specialist`, `consultant` |
| `assigned_date` | DATE | Yes | When assignment was made |
| `assigned_by` | UUID | No | Who made the assignment |
| `status` | ENUM | Yes | `active`, `inactive`, `transferred` |
| `notes` | TEXT | No | Assignment notes |
| `created_at` | TIMESTAMPTZ | Yes | Record creation |

---

## 5. Additional Tables

### Healthcare Facilities
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `name` | VARCHAR(255) | Yes | Facility name |
| `type` | ENUM | Yes | Facility type (see doctor profile) |
| `address` | TEXT | Yes | Full address |
| `ward` | VARCHAR(100) | Yes | Ward/Commune |
| `district` | VARCHAR(100) | Yes | District |
| `province` | VARCHAR(100) | Yes | Province/City |
| `phone` | VARCHAR(20) | No | Main phone |
| `email` | VARCHAR(255) | No | Facility email |
| `bed_count` | INTEGER | No | Number of beds |
| `services` | TEXT[] | No | Available services |
| `operating_hours` | JSONB | No | Hours of operation |
| `emergency_available` | BOOLEAN | No | 24/7 emergency services |
| `created_at` | TIMESTAMPTZ | Yes | Record creation |
| `updated_at` | TIMESTAMPTZ | Yes | Last update |

### Vital Signs Log
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `patient_id` | UUID | Yes | FK to patients |
| `recorded_at` | TIMESTAMPTZ | Yes | When measurement was taken |
| `recorded_by` | UUID | No | Doctor/Nurse who recorded |
| `blood_pressure_systolic` | INTEGER | No | Systolic BP (mmHg) |
| `blood_pressure_diastolic` | INTEGER | No | Diastolic BP (mmHg) |
| `heart_rate` | INTEGER | No | BPM |
| `blood_glucose` | DECIMAL(5,2) | No | mmol/L |
| `blood_glucose_timing` | ENUM | No | `fasting`, `before_meal`, `after_meal`, `random` |
| `temperature` | DECIMAL(4,2) | No | Celsius |
| `oxygen_saturation` | INTEGER | No | SpO2 percentage |
| `weight_kg` | DECIMAL(5,2) | No | Weight at time |
| `notes` | TEXT | No | Additional observations |
| `source` | ENUM | No | `self_reported`, `clinic`, `hospital`, `device` |

---

## Notes for Implementation

1. **Vietnamese Context**: Many fields are designed for Vietnam's healthcare system (BHYT insurance, administrative divisions, ID types).

2. **Chronic Disease Focus**: The schema emphasizes chronic condition management with detailed tracking fields.

3. **Offline-First Consideration**: JSONB fields allow flexible offline data storage that syncs when connected.

4. **Privacy Compliance**: Sensitive data (national_id, medical records) should be encrypted at rest.

5. **Multilingual**: Default language is Vietnamese (`vi`), with English (`en`) support.

6. **ICD-10 Codes**: Use standard ICD-10 codes for conditions to enable interoperability.
