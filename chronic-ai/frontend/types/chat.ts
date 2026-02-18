/**
 * Chat and consultation types
 */

export interface ChatMessage {
    id: string
    role: "user" | "assistant"
    content: string
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
    patient_id: string
}

export interface ChatStreamUpdate {
    stage:
        | "starting"
        | "translating_input"
        | "translated_input"
        | "verifying_input"
        | "verified_input"
        | "scope_blocked"
        | "retrieving_context"
        | "retrieved_context"
        | "retrieved_history"
        | "triaged"
        | "escalated"
        | "medical_reasoning"
        | "reasoned"
        | "translating_output"
        | "formatting_output"
        | "formatted"
        | "complete"
        | "hitl_required"
        | "error"
    message: string
    progress: number
    response?: string
    error?: string
    attachments?: ChatAttachment[]
    thread_id?: string
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

export interface PatientConfirmationDetails {
    matches?: Array<{ id: string; name: string; match_confidence?: number }>
    ambiguous?: Array<{ name: string; score: number; search_term: string; fuzzy_match?: boolean }>
    search_terms?: string[]
    require_single_selection?: boolean
    selection_reason?: string
    validation_error?: string
}

export interface PatientMention {
    id: string
    name: string
    match_confidence: number
}

export interface DoctorChatStreamUpdate {
    stage:
    | "starting"
    | "translating_input"
    | "translated_input"
    | "verifying_input"
    | "verified_input"
    | "extracting_patients"
    | "extracted_patients"
    | "resolving_patients"
    | "resolved_patients"
    | "retrieving_context"
    | "retrieved_context"
    | "medical_reasoning"
    | "reasoned"
    | "safety_check"
    | "safety_checked"
    | "formatting_output"
    | "formatted"
    | "translating_output"
    | "complete"
    | "hitl_required"
    | "error"
    message: string
    progress: number
    response?: string
    mentioned_patients?: PatientMention[]
    error?: string
    attachments?: ChatAttachment[]
    formatted_response?: {
        sections: Array<{
            type: string
            icon: string
            title: string
            content?: string
            items?: string[]
        }>
        confidence: number
        sources: string[]
        raw_text: string
    }
    safety_score?: number
    hitl_request?: {
        type: "clarification_needed" | "approval_required" | "patient_confirmation" | "safety_review"
        message: string
        details: Record<string, unknown> | PatientConfirmationDetails
        options?: string[]
    }
    thread_id?: string
}
