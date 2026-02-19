/**
 * Chat API functions
 */

import { apiClient, streamingFetch, uploadFile } from "./client"
import type {
    ChatRequest,
    ChatResponse,
    ChatStreamUpdate,
    ConsultationHistoryResponse,
    ClinicalSummaryRequest,
    ClinicalSummaryResponse,
    UploadResponse,
    DoctorChatStreamUpdate,
    ConversationListResponse,
    ConversationMessagesResponse,
    ChatConversation,
} from "@/types"

/**
 * Send a chat message (non-streaming)
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return apiClient<ChatResponse>("/chat/", {
        method: "POST",
        body: JSON.stringify(request),
    })
}

/**
 * Send a chat message with streaming response
 */
export async function* sendChatMessageStreaming(
    request: ChatRequest,
    conversationId?: string,
): AsyncGenerator<ChatStreamUpdate> {
    yield* streamingFetch<ChatStreamUpdate>("/chat/patient/v2/stream", {
        patient_id: request.patient_id,
        message: request.message,
        image_path: request.image_path,
        output_format: "structured",
        conversation_id: conversationId,
    })
}

/**
 * Get chat history for a patient
 */
export async function getChatHistory(
    patientId: string,
    limit = 20
): Promise<ConsultationHistoryResponse> {
    return apiClient<ConsultationHistoryResponse>(
        `/chat/history/${patientId}?limit=${limit}`
    )
}

/**
 * Generate clinical summary for a consultation
 */
export async function generateClinicalSummary(
    request: ClinicalSummaryRequest
): Promise<ClinicalSummaryResponse> {
    return apiClient<ClinicalSummaryResponse>("/doctor/summary", {
        method: "POST",
        body: JSON.stringify(request),
    })
}

/**
 * Upload a medical document
 */
export async function uploadDocument(
    file: File,
    patientId: string,
    recordType: string,
    title?: string
): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("patient_id", patientId)
    formData.append("record_type", recordType)
    if (title) formData.append("title", title)

    return uploadFile<UploadResponse>("/upload/document", formData)
}

/**
 * Upload text content directly
 */
export async function uploadTextRecord(
    patientId: string,
    recordType: string,
    content: string,
    title?: string
): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append("patient_id", patientId)
    formData.append("record_type", recordType)
    formData.append("content", content)
    if (title) formData.append("title", title)

    return uploadFile<UploadResponse>("/upload/text", formData)
}

/**
 * Upload an image temporarily for chat use.
 * Returns the file path that can be used with chat endpoints.
 */
export async function uploadChatImage(file: File): Promise<{ file_path: string }> {
    const formData = new FormData()
    formData.append("file", file)
    return uploadFile<{ file_path: string; status: string; message: string }>("/upload/chat-image", formData)
}

/**
 * Send doctor orchestrator message with streaming response.
 * This allows doctors to ask about any patient without pre-selection.
 */
export async function* sendDoctorChatStreaming(
    message: string,
    imagePath?: string,
    conversationId?: string,
    doctorId?: string,
): AsyncGenerator<DoctorChatStreamUpdate> {
    yield* streamingFetch<DoctorChatStreamUpdate>("/chat/doctor/v2/stream", {
        message,
        image_path: imagePath,
        enable_hitl: false,
        enable_llm_hitl: false,
        enable_patient_confirmation_hitl: true,
        output_format: "structured",
        conversation_id: conversationId,
        doctor_id: doctorId,
    })
}

/**
 * Resume doctor orchestrator stream after a HITL interrupt.
 */
export async function* resumeDoctorChatStreaming(
    threadId: string,
    response: Record<string, unknown>
): AsyncGenerator<DoctorChatStreamUpdate> {
    yield* streamingFetch<DoctorChatStreamUpdate>("/chat/doctor/v2/resume", {
        thread_id: threadId,
        response,
    })
}


// ============================================================================
// Conversation Management
// ============================================================================

/**
 * List conversations for a user.
 */
export async function getConversations(
    type: "doctor" | "patient",
    userId: string,
    limit = 50
): Promise<ConversationListResponse> {
    return apiClient<ConversationListResponse>(
        `/chat/conversations/${type}?user_id=${userId}&limit=${limit}`
    )
}

/**
 * Get messages for a specific conversation.
 */
export async function getConversationMessages(
    conversationId: string,
    limit = 100
): Promise<ConversationMessagesResponse> {
    return apiClient<ConversationMessagesResponse>(
        `/chat/conversations/${conversationId}/messages?limit=${limit}`
    )
}

/**
 * Create a new conversation.
 */
export async function createConversation(
    type: "doctor" | "patient",
    userId: string,
    title?: string
): Promise<ChatConversation> {
    return apiClient<ChatConversation>("/chat/conversations", {
        method: "POST",
        body: JSON.stringify({
            conversation_type: type,
            user_id: userId,
            title,
        }),
    })
}

/**
 * Delete a conversation and all its messages.
 */
export async function deleteConversation(
    conversationId: string
): Promise<{ status: string; conversation_id: string }> {
    return apiClient<{ status: string; conversation_id: string }>(
        `/chat/conversations/${conversationId}`,
        { method: "DELETE" }
    )
}
