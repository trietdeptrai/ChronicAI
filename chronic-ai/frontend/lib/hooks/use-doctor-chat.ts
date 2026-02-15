/**
 * Doctor orchestrator chat hook with streaming support.
 * Allows doctors to ask about any patient without pre-selection.
 *
 * Enhanced with:
 * - Human-in-the-loop (HITL) support for clarifications and approvals
 * - Better error handling with user-friendly Vietnamese messages
 * - Safety level indicators
 * - Retry capability for failed requests
 */
"use client"

import { useState, useCallback } from "react"
import { sendDoctorChatStreaming, resumeDoctorChatStreaming } from "@/lib/api"
import type { ChatMessage, DoctorChatStreamUpdate, PatientMention } from "@/types"

// HITL Request type (matches backend HITLRequest)
interface HITLRequest {
    type: "clarification_needed" | "approval_required" | "patient_confirmation" | "safety_review"
    message: string
    details: Record<string, unknown>
    options?: string[]
}

interface UseDoctorChatOptions {
    onStreamUpdate?: (update: DoctorChatStreamUpdate) => void
    onComplete?: (response: string) => void
    onError?: (error: Error) => void
    onHITLRequest?: (request: HITLRequest) => void
}

interface DoctorChatState {
    messages: ChatMessage[]
    isLoading: boolean
    isStreaming: boolean
    currentStage?: DoctorChatStreamUpdate["stage"]
    currentStageMessage?: string
    currentProgress: number
    mentionedPatients: PatientMention[]
    error?: string
    // HITL state
    pendingHITL?: HITLRequest
    threadId?: string
    // Safety indicators
    safetyScore?: number
    safetyLevel?: "safe" | "caution" | "warning" | "critical"
}

// User-friendly Vietnamese stage messages for better UX
const STAGE_MESSAGES: Record<string, string> = {
    starting: "Đang bắt đầu xử lý...",
    translating_input: "Đang phân tích câu hỏi...",
    translated_input: "Đã hiểu câu hỏi",
    verifying_input: "Đang kiểm tra độ rõ ràng...",
    verified_input: "Câu hỏi rõ ràng",
    extracting_patients: "Đang xác định bệnh nhân...",
    extracted_patients: "Đã xác định bệnh nhân",
    resolving_patients: "Đang tra cứu hồ sơ bệnh nhân...",
    resolved_patients: "Đã tìm thấy hồ sơ",
    retrieving_context: "Đang tổng hợp thông tin y tế...",
    retrieved_context: "Đã tổng hợp thông tin",
    medical_reasoning: "Đang phân tích y khoa...",
    reasoned: "Đã hoàn thành phân tích",
    safety_check: "Đang kiểm tra an toàn...",
    safety_checked: "Đã kiểm tra an toàn",
    formatting_output: "Đang định dạng kết quả...",
    formatted: "Đã định dạng",
    complete: "Hoàn thành ✓",
    error: "Đã xảy ra lỗi",
    hitl_required: "⏸️ Cần xác nhận từ bác sĩ",
}

/**
 * Hook for doctor orchestrator chat with streaming support.
 * Unlike useChat, this does not require a patient_id.
 *
 * Features:
 * - Real-time streaming progress updates
 * - HITL (Human-in-the-Loop) support for clarifications
 * - Safety indicators for medical responses
 * - User-friendly Vietnamese error messages
 */
export function useDoctorChat({ onStreamUpdate, onComplete, onError, onHITLRequest }: UseDoctorChatOptions = {}) {
    const [state, setState] = useState<DoctorChatState>({
        messages: [],
        isLoading: false,
        isStreaming: false,
        currentProgress: 0,
        mentionedPatients: [],
    })

    /**
     * Get user-friendly stage message in Vietnamese
     */
    const getStageMessage = (stage: string, serverMessage?: string): string => {
        return serverMessage || STAGE_MESSAGES[stage] || "Đang xử lý..."
    }

    /**
     * Send a message with streaming response
     */
    const sendMessage = useCallback(async (message: string, imagePath?: string) => {
        // Add user message
        const userMessage: ChatMessage = {
            id: `user-${Date.now()}`,
            role: "user",
            content: message,
            timestamp: new Date().toISOString(),
        }

        setState(prev => ({
            ...prev,
            messages: [...prev.messages, userMessage],
            isLoading: true,
            isStreaming: true,
            currentStage: "starting" as DoctorChatStreamUpdate["stage"],
            currentStageMessage: STAGE_MESSAGES.starting,
            currentProgress: 0,
            mentionedPatients: [],
            error: undefined,
            pendingHITL: undefined,
            safetyScore: undefined,
            safetyLevel: undefined,
        }))

        try {
            let finalResponse = ""
            let mentionedPatients: PatientMention[] = []
            let didComplete = false

            for await (const update of sendDoctorChatStreaming(message, imagePath)) {
                onStreamUpdate?.(update)

                // Update state with progress and stage message
                setState(prev => ({
                    ...prev,
                    currentStage: update.stage,
                    currentStageMessage: getStageMessage(update.stage, update.message),
                    currentProgress: update.progress,
                }))

                // Track mentioned patients as they're resolved
                if (update.mentioned_patients) {
                    mentionedPatients = update.mentioned_patients
                    setState(prev => ({
                        ...prev,
                        mentionedPatients: update.mentioned_patients || [],
                    }))
                }

                // Handle safety score updates (extended field from backend)
                const extendedUpdate = update as DoctorChatStreamUpdate & {
                    safety_score?: number
                    hitl_request?: HITLRequest
                    thread_id?: string
                }

                if (extendedUpdate.safety_score !== undefined) {
                    const score = extendedUpdate.safety_score
                    const safetyLevel = score >= 0.9 ? "safe" :
                                       score >= 0.7 ? "caution" :
                                       score >= 0.5 ? "warning" : "critical"
                    setState(prev => ({
                        ...prev,
                        safetyScore: score,
                        safetyLevel,
                    }))
                }
                if (extendedUpdate.thread_id) {
                    setState(prev => ({
                        ...prev,
                        threadId: extendedUpdate.thread_id,
                    }))
                }

                // Handle HITL (Human-in-the-Loop) requests
                // Backend sends stage as "hitl_required" when human input needed
                if ((update.stage as string) === "hitl_required" && extendedUpdate.hitl_request) {
                    const hitlRequest = extendedUpdate.hitl_request
                    setState(prev => ({
                        ...prev,
                        pendingHITL: hitlRequest,
                        isStreaming: false, // Pause streaming for human input
                    }))
                    onHITLRequest?.(hitlRequest)
                    // Don't continue processing - wait for human response
                    return
                }

                if (update.stage === "complete" && update.response) {
                    if (didComplete) {
                        continue
                    }
                    didComplete = true
                    finalResponse = update.response

                    const assistantMessage: ChatMessage = {
                        id: `assistant-${Date.now()}`,
                        role: "assistant",
                        content: update.response,
                        timestamp: new Date().toISOString(),
                        attachments: update.attachments,
                    }

                    setState(prev => ({
                        ...prev,
                        messages: [...prev.messages, assistantMessage],
                        isLoading: false,
                        isStreaming: false,
                        currentStage: "complete" as DoctorChatStreamUpdate["stage"],
                        currentStageMessage: STAGE_MESSAGES.complete,
                        currentProgress: 1,
                        mentionedPatients: update.mentioned_patients || mentionedPatients,
                    }))

                    onComplete?.(update.response)
                }

                if (update.stage === "error") {
                    throw new Error(update.error || update.message || "Đã xảy ra lỗi không xác định")
                }
            }

            return finalResponse
        } catch (error) {
            // User-friendly Vietnamese error messages
            let errorMessage = "Đã xảy ra lỗi. Vui lòng thử lại."

            if (error instanceof Error) {
                const errStr = error.message.toLowerCase()
                if (errStr.includes("timeout") || errStr.includes("timed out")) {
                    errorMessage = "Hệ thống đang phản hồi chậm. Vui lòng thử lại sau ít phút."
                } else if (errStr.includes("connection") || errStr.includes("network")) {
                    errorMessage = "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng."
                } else if (errStr.includes("circuit breaker")) {
                    errorMessage = "Hệ thống đang quá tải. Vui lòng thử lại sau ít phút."
                } else if (error.message) {
                    errorMessage = error.message
                }
            }

            setState(prev => ({
                ...prev,
                isLoading: false,
                isStreaming: false,
                currentStage: "error" as DoctorChatStreamUpdate["stage"],
                currentStageMessage: errorMessage,
                error: errorMessage,
            }))
            onError?.(error instanceof Error ? error : new Error(errorMessage))
            throw error
        }
    }, [onStreamUpdate, onComplete, onError, onHITLRequest])

    /**
     * Resume a paused HITL conversation.
     */
    const resumeHITL = useCallback(async (response: Record<string, unknown>) => {
        if (!state.threadId) {
            throw new Error("Không tìm thấy thread để tiếp tục HITL")
        }

        setState(prev => ({
            ...prev,
            isLoading: true,
            isStreaming: true,
            error: undefined,
            pendingHITL: undefined,
        }))

        try {
            let finalResponse = ""
            let mentionedPatients: PatientMention[] = state.mentionedPatients
            let didComplete = false

            for await (const update of resumeDoctorChatStreaming(state.threadId, response)) {
                onStreamUpdate?.(update)

                setState(prev => ({
                    ...prev,
                    currentStage: update.stage,
                    currentStageMessage: getStageMessage(update.stage, update.message),
                    currentProgress: update.progress,
                }))

                if (update.mentioned_patients) {
                    mentionedPatients = update.mentioned_patients
                    setState(prev => ({
                        ...prev,
                        mentionedPatients: update.mentioned_patients || [],
                    }))
                }

                const extendedUpdate = update as DoctorChatStreamUpdate & {
                    safety_score?: number
                    hitl_request?: HITLRequest
                    thread_id?: string
                }

                if (extendedUpdate.safety_score !== undefined) {
                    const score = extendedUpdate.safety_score
                    const safetyLevel = score >= 0.9 ? "safe" :
                                       score >= 0.7 ? "caution" :
                                       score >= 0.5 ? "warning" : "critical"
                    setState(prev => ({
                        ...prev,
                        safetyScore: score,
                        safetyLevel,
                    }))
                }
                if (extendedUpdate.thread_id) {
                    setState(prev => ({
                        ...prev,
                        threadId: extendedUpdate.thread_id,
                    }))
                }

                if ((update.stage as string) === "hitl_required" && extendedUpdate.hitl_request) {
                    const hitlRequest = extendedUpdate.hitl_request
                    setState(prev => ({
                        ...prev,
                        pendingHITL: hitlRequest,
                        isStreaming: false,
                    }))
                    onHITLRequest?.(hitlRequest)
                    return
                }

                if (update.stage === "complete" && update.response) {
                    if (didComplete) {
                        continue
                    }
                    didComplete = true
                    finalResponse = update.response

                    const assistantMessage: ChatMessage = {
                        id: `assistant-${Date.now()}`,
                        role: "assistant",
                        content: update.response,
                        timestamp: new Date().toISOString(),
                        attachments: update.attachments,
                    }

                    setState(prev => ({
                        ...prev,
                        messages: [...prev.messages, assistantMessage],
                        isLoading: false,
                        isStreaming: false,
                        currentStage: "complete" as DoctorChatStreamUpdate["stage"],
                        currentStageMessage: STAGE_MESSAGES.complete,
                        currentProgress: 1,
                        mentionedPatients: update.mentioned_patients || mentionedPatients,
                        pendingHITL: undefined,
                    }))

                    onComplete?.(update.response)
                }

                if (update.stage === "error") {
                    throw new Error(update.error || update.message || "Đã xảy ra lỗi không xác định")
                }
            }

            return finalResponse
        } catch (error) {
            let errorMessage = "Đã xảy ra lỗi khi tiếp tục xác nhận. Vui lòng thử lại."

            if (error instanceof Error && error.message) {
                errorMessage = error.message
            }

            setState(prev => ({
                ...prev,
                isLoading: false,
                isStreaming: false,
                currentStage: "error" as DoctorChatStreamUpdate["stage"],
                currentStageMessage: errorMessage,
                error: errorMessage,
            }))
            onError?.(error instanceof Error ? error : new Error(errorMessage))
            throw error
        }
    }, [state.threadId, state.mentionedPatients, onStreamUpdate, onComplete, onError, onHITLRequest])

    /**
     * Clear chat history
     */
    const clearMessages = useCallback(() => {
        setState({
            messages: [],
            isLoading: false,
            isStreaming: false,
            currentProgress: 0,
            mentionedPatients: [],
            error: undefined,
            pendingHITL: undefined,
            safetyScore: undefined,
            safetyLevel: undefined,
        })
    }, [])

    /**
     * Clear current error and allow retry
     */
    const clearError = useCallback(() => {
        setState(prev => ({
            ...prev,
            error: undefined,
            currentStage: undefined,
            currentStageMessage: undefined,
        }))
    }, [])

    /**
     * Dismiss pending HITL request (cancel the operation)
     */
    const dismissHITL = useCallback(() => {
        setState(prev => ({
            ...prev,
            pendingHITL: undefined,
            isLoading: false,
            isStreaming: false,
        }))
    }, [])

    return {
        // State
        ...state,
        // Computed values
        hasError: !!state.error,
        hasPendingHITL: !!state.pendingHITL,
        isSafeResponse: state.safetyLevel === "safe" || state.safetyLevel === "caution",
        // Actions
        sendMessage,
        resumeHITL,
        clearMessages,
        clearError,
        dismissHITL,
    }
}
