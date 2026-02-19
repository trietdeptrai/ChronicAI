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
  surgical_history?: Array<Record<string, unknown> | string>
  medical_history?: MedicalHistory
  family_medical_history?: FamilyMedicalHistory | Record<string, unknown>
  immunization_records?: ImmunizationRecords
  treatment_history?: TreatmentHistory
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
  profile_status: "active" | "inactive" | "deceased" | "suspended"
  created_at: string
  updated_at: string
}

export interface PatientCreateInput {
  full_name: string
  date_of_birth: string
  gender: "male" | "female" | "other"
  national_id?: string
  insurance_number?: string
  phone_primary: string
  phone_secondary?: string
  email?: string
  address_street?: string
  address_ward: string
  address_district: string
  address_province: string
  emergency_contact_name: string
  emergency_contact_phone: string
  emergency_contact_relationship: string
  blood_type?: "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-" | "unknown"
  primary_diagnosis?: string
  triage_priority?: "low" | "medium" | "high" | "urgent"
  profile_status?: "active" | "inactive" | "deceased" | "suspended"
  preferred_language?: "vi" | "en"
  assigned_doctor_id?: string
}

export interface PatientUpdateInput {
  full_name?: string
  date_of_birth?: string
  gender?: "male" | "female" | "other"
  national_id?: string | null
  insurance_number?: string | null
  phone_primary?: string
  phone_secondary?: string | null
  email?: string | null
  address_street?: string | null
  address_ward?: string
  address_district?: string
  address_province?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  emergency_contact_relationship?: string
  blood_type?: "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-" | "unknown"
  primary_diagnosis?: string | null
  triage_priority?: "low" | "medium" | "high" | "urgent"
  profile_status?: "active" | "inactive" | "deceased" | "suspended"
  preferred_language?: "vi" | "en"
  assigned_doctor_id?: string | null
  chronic_conditions?: Array<Record<string, unknown> | string>
  surgical_history?: Array<Record<string, unknown> | string>
  allergies?: string[]
  family_medical_history?: FamilyMedicalHistory | Record<string, unknown> | null
  medical_history?: MedicalHistory | Record<string, unknown> | null
  immunization_records?: ImmunizationRecords | Record<string, unknown> | null
  treatment_history?: TreatmentHistory | Record<string, unknown> | null
}

export interface PatientMutationResponse {
  status: string
  patient: Patient
  message: string
}

export interface DeletePatientResponse {
  status: string
  patient_id: string
  user_id?: string | null
  warning?: string
  message: string
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

export interface MedicalHistory {
  chronic_conditions?: Array<Record<string, unknown> | string>
  past_surgeries?: Array<Record<string, unknown> | string>
  hospitalizations?: Array<Record<string, unknown> | string>
  medications_history?: Array<Record<string, unknown> | string>
  allergies?: Array<Record<string, unknown> | string>
  psychiatric_history?: Array<Record<string, unknown> | string>
  [key: string]: unknown
}

export interface FamilyMedicalHistory {
  family_history_of_chronic_conditions?: Array<Record<string, unknown> | string>
  family_history_of_mental_health_conditions?: Array<Record<string, unknown> | string>
  family_history_of_genetic_conditions?: Array<Record<string, unknown> | string>
  [key: string]: unknown
}

export interface ImmunizationRecords {
  vaccines_administered?: Array<Record<string, unknown> | string>
  vaccines_due?: Array<Record<string, unknown> | string>
  [key: string]: unknown
}

export interface TreatmentHistory {
  previous_treatments?: Array<Record<string, unknown> | string>
  physiotherapy?: Array<Record<string, unknown> | string>
  other_relevant_treatments?: Array<Record<string, unknown> | string>
  [key: string]: unknown
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

export interface VitalSignsResponse {
  patient_id: string
  vitals: VitalSign[]
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

export interface VitalSignInput {
  recorded_at?: string
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
