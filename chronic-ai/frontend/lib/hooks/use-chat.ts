/**
 * Chat hooks with streaming support and conversation history persistence
 */
"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
    sendChatMessage,
    sendChatMessageStreaming,
    getChatHistory,
    generateClinicalSummary,
    getConversations,
    getConversationMessages,
    deleteConversation as apiDeleteConversation,
} from "@/lib/api"
import type {
    ChatMessage,
    ChatStreamUpdate,
    ChatRequest,
    ConsultationHistoryResponse,
    ClinicalSummaryRequest,
    ClinicalSummaryResponse,
    ChatConversation,
} from "@/types"

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
    // Conversation history
    conversations: ChatConversation[]
    activeConversationId?: string
    isLoadingConversations: boolean
}

/**
 * Hook for managing chat with streaming support and conversation history
 */
export function useChat({ patientId, onStreamUpdate, onComplete, onError }: UseChatOptions) {
    const [state, setState] = useState<ChatState>({
        messages: [],
        isLoading: false,
        isStreaming: false,
        currentProgress: 0,
        conversations: [],
        isLoadingConversations: false,
    })

    const abortControllerRef = useRef<AbortController | null>(null)

    /**
     * Load conversation list on mount / patientId change
     */
    useEffect(() => {
        if (!patientId) return

        let cancelled = false
        setState(prev => ({ ...prev, isLoadingConversations: true }))

        getConversations("patient", patientId)
            .then(res => {
                if (!cancelled) {
                    setState(prev => ({
                        ...prev,
                        conversations: res.conversations,
                        isLoadingConversations: false,
                    }))
                }
            })
            .catch(() => {
                if (!cancelled) {
                    setState(prev => ({ ...prev, isLoadingConversations: false }))
                }
            })

        return () => { cancelled = true }
    }, [patientId])

    /**
     * Refresh conversations list
     */
    const refreshConversations = useCallback(async () => {
        if (!patientId) return
        try {
            const res = await getConversations("patient", patientId)
            setState(prev => ({ ...prev, conversations: res.conversations }))
        } catch {
            // silent fail
        }
    }, [patientId])

    /**
     * Load a specific conversation's messages
     */
    const loadConversation = useCallback(async (conversationId: string) => {
        try {
            const res = await getConversationMessages(conversationId)
            const msgs: ChatMessage[] = res.messages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                timestamp: m.created_at,
                attachments: (m.metadata as Record<string, unknown>)?.attachments as ChatMessage["attachments"],
            }))
            setState(prev => ({
                ...prev,
                messages: msgs,
                activeConversationId: conversationId,
                error: undefined,
            }))
        } catch (error) {
            console.error("Failed to load conversation:", error)
        }
    }, [])

    /**
     * Start a new conversation (clears messages)
     */
    const newConversation = useCallback(() => {
        setState(prev => ({
            ...prev,
            messages: [],
            activeConversationId: undefined,
            error: undefined,
            currentProgress: 0,
        }))
    }, [])

    /**
     * Delete a conversation
     */
    const deleteConversation = useCallback(async (conversationId: string) => {
        try {
            await apiDeleteConversation(conversationId)
            setState(prev => ({
                ...prev,
                conversations: prev.conversations.filter(c => c.id !== conversationId),
                // If we deleted the active conversation, clear messages
                ...(prev.activeConversationId === conversationId
                    ? { messages: [], activeConversationId: undefined }
                    : {}),
            }))
        } catch (error) {
            console.error("Failed to delete conversation:", error)
        }
    }, [])

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
            let didComplete = false
            let newConversationId = state.activeConversationId

            for await (const update of sendChatMessageStreaming(request, state.activeConversationId)) {
                onStreamUpdate?.(update)

                // Capture conversation_id from backend
                const rawUpdate = update as unknown as Record<string, unknown>
                if (rawUpdate.conversation_id && !newConversationId) {
                    newConversationId = rawUpdate.conversation_id as string
                }

                setState(prev => ({
                    ...prev,
                    currentStage: update.stage,
                    currentProgress: update.progress,
                }))

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
                        currentStage: undefined,
                        currentProgress: 1,
                        activeConversationId: newConversationId || prev.activeConversationId,
                    }))

                    onComplete?.(update.response)
                }

                if (update.stage === "error") {
                    throw new Error(update.error || update.message)
                }
            }

            // Refresh conversation list to pick up the new/updated conversation
            refreshConversations()

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
    }, [patientId, state.activeConversationId, onStreamUpdate, onComplete, onError, refreshConversations])

    /**
     * Clear chat history (local state only)
     */
    const clearMessages = useCallback(() => {
        setState(prev => ({
            ...prev,
            messages: [],
            isLoading: false,
            isStreaming: false,
            currentProgress: 0,
            activeConversationId: undefined,
        }))
    }, [])

    return {
        ...state,
        sendMessage,
        clearMessages,
        loadConversation,
        newConversation,
        deleteConversation,
        refreshConversations,
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
