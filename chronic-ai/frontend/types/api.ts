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
