/**
 * API response types
 */

export interface ApiError {
    code: string
    message: string
    details?: Record<string, unknown>
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
    chunks_created?: number
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
    record_type: "prescription" | "lab" | "xray" | "ecg" | "notes" | "referral"
    title: string
    content_text?: string
    analysis_result?: string
    is_verified?: boolean
    created_at: string
}

export interface MedicalRecordsResponse {
    patient_id: string
    records: MedicalRecord[]
}
