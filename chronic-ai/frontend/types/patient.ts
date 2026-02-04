/**
 * Patient type definitions matching the backend data models.
 */

export interface Patient {
  id: string
  user_id: string
  full_name: string
  date_of_birth: string
  gender: "male" | "female" | "other"
  national_id?: string
  phone_primary: string
  phone_secondary?: string
  email?: string
  profile_photo_url?: string

  // Address
  address_street?: string
  address_ward: string
  address_district: string
  address_province: string

  // Emergency Contact
  emergency_contact_name: string
  emergency_contact_phone: string
  emergency_contact_relationship: string

  // Medical Demographics
  blood_type?: "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-" | "unknown"
  height_cm?: number
  weight_kg?: number
  bmi?: number

  // Chronic Conditions
  chronic_conditions: ChronicCondition[]
  primary_diagnosis?: string
  diagnosis_date?: string
  disease_stage?: string

  // Medications
  current_medications?: Medication[]
  medication_adherence_score?: number

  // Medical History
  allergies?: string[]
  smoking_status?: "never" | "former" | "current"
  alcohol_consumption?: "none" | "occasional" | "moderate" | "heavy"

  // Insurance
  insurance_provider?: string
  insurance_number?: string
  insurance_expiry?: string

  // App Fields
  preferred_language: "vi" | "en"
  assigned_doctor_id?: string
  last_checkup_date?: string
  next_appointment_date?: string
  triage_priority?: "low" | "medium" | "high" | "urgent"
  profile_status: "active" | "inactive" | "deceased"
  created_at: string
  updated_at: string
}

export interface ChronicCondition {
  icd10_code: string
  name: string
  diagnosed_date?: string
  stage?: string
  notes?: string
}

export interface Medication {
  name: string
  dosage: string
  frequency: string
  timing?: string
  prescriber?: string
  start_date?: string
}

/**
 * API response types
 */
export interface PatientListResponse {
  patients: Patient[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PatientDetailResponse {
  patient: Patient
  recent_vitals: VitalSign[]
  recent_consultations: ConsultationSummary[]
}

export interface VitalSign {
  id: string
  patient_id: string
  recorded_at: string
  recorded_by?: string
  blood_pressure_systolic?: number
  blood_pressure_diastolic?: number
  heart_rate?: number
  blood_glucose?: number
  blood_glucose_timing?: "fasting" | "before_meal" | "after_meal" | "random"
  temperature?: number
  oxygen_saturation?: number
  weight_kg?: number
  notes?: string
  source?: "self_reported" | "clinic" | "hospital" | "device"
}

export interface ConsultationSummary {
  id: string
  chief_complaint?: string
  status: string
  priority?: string
  started_at: string
  summary?: string
}
