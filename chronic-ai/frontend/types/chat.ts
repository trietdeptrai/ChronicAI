/**
 * Chat and consultation types
 */

export interface ChatMessage {
    id: string
    role: "user" | "assistant"
    content: string
    content_en?: string
    timestamp: string
}

export interface ChatRequest {
    patient_id: string
    message: string
    image_path?: string
}

export interface ChatResponse {
    response: string
    response_en?: string
    patient_id: string
}

export interface ChatStreamUpdate {
    stage: "translating_input" | "retrieving_context" | "medical_reasoning" | "translating_output" | "complete" | "error"
    message: string
    progress: number
    response?: string
    response_en?: string
    error?: string
}

export interface Consultation {
    id: string
    patient_id: string
    doctor_id?: string
    chief_complaint?: string
    status: "triage" | "urgent" | "in_progress" | "completed" | "cancelled"
    priority?: "low" | "medium" | "high" | "urgent"
    started_at: string
    ended_at?: string
    messages: ChatMessage[]
    summary?: string
}

export interface ConsultationHistoryResponse {
    patient_id: string
    consultations: Consultation[]
}

export interface ClinicalSummaryRequest {
    consultation_id: string
    patient_id: string
}

export interface ClinicalSummaryResponse {
    consultation_id: string
    patient_id: string
    summary: string
}
