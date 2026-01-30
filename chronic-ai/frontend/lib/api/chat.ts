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
    request: ChatRequest
): AsyncGenerator<ChatStreamUpdate> {
    yield* streamingFetch<ChatStreamUpdate>("/chat/stream", request)
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
