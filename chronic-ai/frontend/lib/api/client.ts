/**
 * Base API client for backend communication
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface FetchOptions extends RequestInit {
    timeout?: number
}

/**
 * Generic API client function with error handling and timeout support
 */
export async function apiClient<T>(
    endpoint: string,
    options: FetchOptions = {}
): Promise<T> {
    const { timeout = 30000, ...fetchOptions } = options
    const url = `${API_BASE}${endpoint}`

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                ...fetchOptions.headers,
            },
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new ApiError(
                response.status,
                errorData.detail || `HTTP error ${response.status}`,
                errorData
            )
        }

        return response.json()
    } catch (error) {
        clearTimeout(timeoutId)

        if (error instanceof ApiError) {
            throw error
        }

        if (error instanceof Error) {
            if (error.name === "AbortError") {
                throw new ApiError(408, "Request timeout")
            }
            throw new ApiError(500, error.message)
        }

        throw new ApiError(500, "Unknown error occurred")
    }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
        public data?: Record<string, unknown>
    ) {
        super(message)
        this.name = "ApiError"
    }
}

/**
 * Streaming fetch for SSE endpoints (chat streaming)
 */
export async function* streamingFetch<T>(
    endpoint: string,
    body: object
): AsyncGenerator<T> {
    const url = `${API_BASE}${endpoint}`

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
            response.status,
            errorData.detail || `HTTP error ${response.status}`,
            errorData
        )
    }

    const reader = response.body?.getReader()
    if (!reader) {
        throw new ApiError(500, "No response body")
    }

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
            if (line.startsWith("data: ")) {
                const data = line.slice(6)
                try {
                    yield JSON.parse(data) as T
                } catch {
                    // Skip invalid JSON
                }
            }
        }
    }
}

/**
 * Upload file with form data
 */
export async function uploadFile<T>(
    endpoint: string,
    formData: FormData,
    method: "POST" | "PUT" | "PATCH" = "POST"
): Promise<T> {
    const url = `${API_BASE}${endpoint}`

    const response = await fetch(url, {
        method,
        body: formData,
        // Don't set Content-Type header - browser will set it with boundary
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
            response.status,
            errorData.detail || `HTTP error ${response.status}`,
            errorData
        )
    }

    return response.json()
}
