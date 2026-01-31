/**
 * Doctor orchestrator chat hook with streaming support.
 * Allows doctors to ask about any patient without pre-selection.
 */
"use client"

import { useState, useCallback } from "react"
import { sendDoctorChatStreaming } from "@/lib/api"
import type { ChatMessage, DoctorChatStreamUpdate, PatientMention } from "@/types"

interface UseDoctorChatOptions {
    onStreamUpdate?: (update: DoctorChatStreamUpdate) => void
    onComplete?: (response: string) => void
    onError?: (error: Error) => void
}

interface DoctorChatState {
    messages: ChatMessage[]
    isLoading: boolean
    isStreaming: boolean
    currentStage?: DoctorChatStreamUpdate["stage"]
    currentProgress: number
    mentionedPatients: PatientMention[]
    error?: string
}

/**
 * Hook for doctor orchestrator chat with streaming support.
 * Unlike useChat, this does not require a patient_id.
 */
export function useDoctorChat({ onStreamUpdate, onComplete, onError }: UseDoctorChatOptions = {}) {
    const [state, setState] = useState<DoctorChatState>({
        messages: [],
        isLoading: false,
        isStreaming: false,
        currentProgress: 0,
        mentionedPatients: [],
    })

    /**
     * Send a message with streaming response
     */
    const sendMessage = useCallback(async (message: string) => {
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
            mentionedPatients: [],
            error: undefined,
        }))

        try {
            let finalResponse = ""
            let mentionedPatients: PatientMention[] = []

            for await (const update of sendDoctorChatStreaming(message)) {
                onStreamUpdate?.(update)

                setState(prev => ({
                    ...prev,
                    currentStage: update.stage,
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

                if (update.stage === "complete" && update.response) {
                    finalResponse = update.response

                    const assistantMessage: ChatMessage = {
                        id: `assistant-${Date.now()}`,
                        role: "assistant",
                        content: update.response,
                        content_en: update.response_en,
                        timestamp: new Date().toISOString(),
                    }

                    setState(prev => ({
                        ...prev,
                        messages: [...prev.messages, assistantMessage],
                        isLoading: false,
                        isStreaming: false,
                        currentStage: undefined,
                        currentProgress: 1,
                        mentionedPatients: update.mentioned_patients || mentionedPatients,
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
    }, [onStreamUpdate, onComplete, onError])

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
        })
    }, [])

    return {
        ...state,
        sendMessage,
        clearMessages,
    }
}
