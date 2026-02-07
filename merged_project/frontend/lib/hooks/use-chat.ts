/**
 * Chat hooks with streaming support
 */
"use client"

import { useState, useCallback, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { sendChatMessage, sendChatMessageStreaming, getChatHistory, generateClinicalSummary } from "@/lib/api"
import type { ChatMessage, ChatStreamUpdate, ChatRequest, ConsultationHistoryResponse, ClinicalSummaryRequest, ClinicalSummaryResponse } from "@/types"

interface UseChatOptions {
    patientId: string
    onStreamUpdate?: (update: ChatStreamUpdate) => void
    onComplete?: (response: string) => void
    onError?: (error: Error) => void
}

interface ChatState {
    messages: ChatMessage[]
    isLoading: boolean
    isStreaming: boolean
    currentStage?: ChatStreamUpdate["stage"]
    currentProgress: number
    error?: string
}

/**
 * Hook for managing chat with streaming support
 */
export function useChat({ patientId, onStreamUpdate, onComplete, onError }: UseChatOptions) {
    const [state, setState] = useState<ChatState>({
        messages: [],
        isLoading: false,
        isStreaming: false,
        currentProgress: 0,
    })

    const abortControllerRef = useRef<AbortController | null>(null)

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
            currentProgress: 0,
            error: undefined,
        }))

        try {
            const request: ChatRequest = {
                patient_id: patientId,
                message,
                image_path: imagePath,
            }

            let finalResponse = ""

            for await (const update of sendChatMessageStreaming(request)) {
                onStreamUpdate?.(update)

                setState(prev => ({
                    ...prev,
                    currentStage: update.stage,
                    currentProgress: update.progress,
                }))

                if (update.stage === "complete" && update.response) {
                    finalResponse = update.response

                    const assistantMessage: ChatMessage = {
                        id: `assistant-${Date.now()}`,
                        role: "assistant",
                        content: update.response,
                        content_en: update.response_en,
                        timestamp: new Date().toISOString(),
                        attachments: update.attachments,
                    }

                    setState(prev => ({
                        ...prev,
                        messages: [...prev.messages, assistantMessage],
                        isLoading: false,
                        isStreaming: false,
                        currentStage: undefined,
                        currentProgress: 1,
                    }))

                    onComplete?.(update.response)
                }

                if (update.stage === "error") {
                    throw new Error(update.error || update.message)
                }
            }

            return finalResponse
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Unknown error"
            setState(prev => ({
                ...prev,
                isLoading: false,
                isStreaming: false,
                error: errorMessage,
            }))
            onError?.(error instanceof Error ? error : new Error(errorMessage))
            throw error
        }
    }, [patientId, onStreamUpdate, onComplete, onError])

    /**
     * Clear chat history
     */
    const clearMessages = useCallback(() => {
        setState({
            messages: [],
            isLoading: false,
            isStreaming: false,
            currentProgress: 0,
        })
    }, [])

    return {
        ...state,
        sendMessage,
        clearMessages,
    }
}

/**
 * Hook for fetching chat history
 */
export function useChatHistory(patientId: string, limit = 20) {
    return useQuery<ConsultationHistoryResponse>({
        queryKey: ["chat-history", patientId, limit],
        queryFn: () => getChatHistory(patientId, limit),
        enabled: !!patientId,
    })
}

/**
 * Hook for generating clinical summary
 */
export function useClinicalSummary() {
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const generate = useCallback(async (request: ClinicalSummaryRequest) => {
        setIsLoading(true)
        setError(null)

        try {
            const result = await generateClinicalSummary(request)
            return result
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to generate summary"
            setError(errorMessage)
            throw err
        } finally {
            setIsLoading(false)
        }
    }, [])

    return { generate, isLoading, error }
}
