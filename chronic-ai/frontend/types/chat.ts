/**
 * Chat and consultation types
 */

export interface ChatMessage {
    id: string
    role: "user" | "assistant"
    content: string
    content_en?: string
    timestamp: string
    attachments?: ChatAttachment[]
}

export interface ChatAttachment {
    type: "image"
    url: string
    title?: string
    record_type?: string
    created_at?: string
    patient_id?: string
    patient_name?: string
    record_id?: string
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
    attachments?: ChatAttachment[]
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

// Doctor Orchestrator Types

export interface DoctorChatRequest {
    message: string
    // No patient_id required - AI extracts from message
}

export interface PatientMention {
    id: string
    name: string
    match_confidence: number
}

export interface DoctorChatStreamUpdate {
    stage:
    | "translating_input"
    | "extracting_patients"
    | "resolving_patients"
    | "retrieving_context"
    | "medical_reasoning"
    | "translating_output"
    | "complete"
    | "error"
    message: string
    progress: number
    response?: string
    response_en?: string
    mentioned_patients?: PatientMention[]
    error?: string
    attachments?: ChatAttachment[]
}
