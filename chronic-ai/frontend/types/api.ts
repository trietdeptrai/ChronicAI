/**
 * API response types
 */

import type { VitalSign } from "./patient"

export interface ApiError {
    code: string
    message: string
    details?: Record<string, unknown>
}

export interface ECGPredictionScore {
    class: string
    description?: string
    score: number
}

export interface ECGClassifierDetails {
    classifier_type?: string
    checkpoint_path?: string
    medsiglip_model_id?: string
    classes?: string[]
    scores?: number[]
    scores_by_class?: Record<string, number>
    predicted_labels?: string[]
    threshold?: number
    [key: string]: unknown
}

export interface MedicalRecordAIAnalysis {
    status?: "completed" | "skipped" | "error"
    summary?: string
    key_findings?: string[]
    clinical_significance?: string
    recommended_follow_up?: string[]
    urgency?: "low" | "medium" | "high"
    confidence?: "low" | "medium" | "high"
    limitations?: string[]
    prediction_scores?: ECGPredictionScore[]
    ecg_classifier?: ECGClassifierDetails
    model?: string
    record_type?: string
    generated_at?: string
    [key: string]: unknown
}

export interface DashboardStats {
    total_patients: number
    urgent_cases: number
    high_priority: number
    pending_consultations: number
    alerts: number
}

export interface UploadResponse {
    status: string
    record_id: string
    patient_id: string
    extracted_text_preview?: string
    ai_analysis?: MedicalRecordAIAnalysis | string | null
    doctor_comment?: string | null
    chunks_created?: number
    warning?: string | null
    message: string
}

export interface PatientPhotoUploadResponse {
    status: string
    patient_id: string
    profile_photo_url: string
    message: string
}

export interface MedicalRecord {
    id: string
    record_type:
    | "prescription"
    | "lab"
    | "xray"
    | "ecg"
    | "ct"
    | "mri"
    | "notes"
    | "referral"
    title: string
    content_text?: string
    analysis_result?: MedicalRecordAIAnalysis | string | null
    doctor_comment?: string | null
    is_verified?: boolean
    created_at: string
    updated_at?: string
    image_url?: string
    file_url?: string
    file_kind?: "image" | "pdf"
}

export interface MedicalRecordsResponse {
    patient_id: string
    records: MedicalRecord[]
}

export interface VitalSignCreateResponse {
    status: string
    vital: VitalSign
}

export interface PatientTextImportResponse {
    status: string
    patient_id: string
    import_format: "zip"
    vitals_imported: number
    consultations_imported: number
    records_imported: number
    files_imported?: number
    warning?: string
    message: string
}

export interface PatientTextImportStartResponse {
    status: "accepted"
    job_id: string
    patient_id: string
    import_format: "zip"
    progress: number
    stage: string
    message: string
}

export interface PatientTextImportStatusResponse {
    job_id: string
    patient_id: string
    import_format: "zip"
    status: "queued" | "running" | "completed" | "failed"
    stage: string
    progress: number
    ocr_current_page?: number | null
    ocr_total_pages?: number | null
    created_at?: string
    updated_at?: string
    error?: string
    result?: PatientTextImportResponse
}

export interface VitalImportPreview {
    recordedAt: string
    source: "self_reported" | "clinic" | "hospital" | "device" | string
    bloodPressureSystolic: string
    bloodPressureDiastolic: string
    heartRate: string
    bloodGlucose: string
    bloodGlucoseTiming: "fasting" | "before_meal" | "after_meal" | "random" | "" | string
    temperature: string
    oxygenSaturation: string
    weightKg: string
    notes: string
}

export interface VitalImportPreviewResponse {
    status: string
    patient_id: string
    total_vitals: number
    prefill: VitalImportPreview
    warning?: string
    message: string
}

export interface MedicalHistoryImportPreview {
    chronic_conditions: unknown[]
    past_surgeries: unknown[]
    hospitalizations: unknown[]
    medications_history: unknown[]
    allergies: unknown[]
    psychiatric_history: unknown[]
    family_history_of_chronic_conditions: unknown[]
    family_history_of_mental_health_conditions: unknown[]
    family_history_of_genetic_conditions: unknown[]
    vaccines_administered: unknown[]
    vaccines_due: unknown[]
    previous_treatments: unknown[]
    physiotherapy: unknown[]
    other_relevant_treatments: unknown[]
}

export interface MedicalHistoryImportPreviewResponse {
    status: string
    patient_id: string
    prefill: MedicalHistoryImportPreview
    warning?: string
    message: string
}

export interface PatientMetadataImportPreview {
    full_name?: string
    date_of_birth?: string
    gender?: "male" | "female" | "other" | string
    national_id?: string
    insurance_number?: string
    primary_diagnosis?: string
    phone_primary?: string
    email?: string
    address_ward?: string
    address_district?: string
    address_province?: string
    emergency_contact_name?: string
    emergency_contact_phone?: string
    emergency_contact_relationship?: string
    triage_priority?: "low" | "medium" | "high" | "urgent" | string
    profile_status?: "active" | "inactive" | "deceased" | "suspended" | string
}

export interface PatientMetadataImportPreviewResponse {
    status: string
    metadata: PatientMetadataImportPreview
    message: string
}

export interface PatientSummaryResponse {
    summary: string
    generated_at: string
    model: string
    error?: string
}
