/**
 * Main chat interface component
 */
"use client"

import { useRef, useEffect } from "react"
import { useChat } from "@/lib/hooks"
import { MessageBubble } from "./message-bubble"
import { ChatInput } from "./chat-input"
import { StreamingProgress } from "./streaming-progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { MessageSquare, Trash2, Globe } from "lucide-react"
import { useState } from "react"

interface ChatInterfaceProps {
    patientId: string
    patientName?: string
}

export function ChatInterface({ patientId, patientName }: ChatInterfaceProps) {
    const [showEnglish, setShowEnglish] = useState(false)
    const scrollRef = useRef<HTMLDivElement>(null)

    const {
        messages,
        isLoading,
        isStreaming,
        currentStage,
        currentProgress,
        error,
        sendMessage,
        clearMessages,
    } = useChat({
        patientId,
        onComplete: () => {
            // Scroll to bottom when response is complete
            setTimeout(() => {
                scrollRef.current?.scrollTo({
                    top: scrollRef.current.scrollHeight,
                    behavior: "smooth",
                })
            }, 100)
        },
    })

    // Scroll to bottom when new messages are added
    useEffect(() => {
        if (messages.length > 0) {
            scrollRef.current?.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth",
            })
        }
    }, [messages.length])

    const handleSend = async (message: string, file?: File) => {
        let imagePath: string | undefined

        // Upload image first if provided
        if (file) {
            try {
                const { uploadChatImage } = await import("@/lib/api")
                const result = await uploadChatImage(file)
                imagePath = result.file_path
            } catch (error) {
                console.error("Failed to upload image:", error)
                // Continue without image if upload fails
            }
        }

        await sendMessage(message, imagePath)
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <MessageSquare className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                        <h3 className="font-medium text-sm">Trợ lý AI Y tế</h3>
                        {patientName && (
                            <p className="text-xs text-muted-foreground">
                                Bệnh nhân: {patientName}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowEnglish(!showEnglish)}
                        className={showEnglish ? "text-primary" : ""}
                    >
                        <Globe className="w-4 h-4 mr-1" />
                        <span className="text-xs">EN</span>
                    </Button>
                    {messages.length > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearMessages}
                            className="text-muted-foreground hover:text-destructive"
                        >
                            <Trash2 className="w-4 h-4" />
                        </Button>
                    )}
                </div>
            </div>

            {/* Messages */}
            <ScrollArea ref={scrollRef} className="flex-1 p-4">
                {messages.length === 0 && !isStreaming ? (
                    <EmptyState />
                ) : (
                    <div className="space-y-4">
                        {messages.map((message) => (
                            <MessageBubble
                                key={message.id}
                                message={message}
                                showEnglish={showEnglish}
                            />
                        ))}

                        {/* Streaming Progress */}
                        {isStreaming && (
                            <StreamingProgress
                                stage={currentStage}
                                progress={currentProgress}
                            />
                        )}

                        {/* Error Message */}
                        {error && (
                            <Card className="p-4 border-destructive/30 bg-destructive/5">
                                <p className="text-sm text-destructive font-medium">Lỗi</p>
                                <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            </Card>
                        )}
                    </div>
                )}
            </ScrollArea>

            {/* Input */}
            <ChatInput
                onSend={handleSend}
                isLoading={isLoading}
                placeholder="Hỏi về sức khỏe, thuốc, hoặc triệu chứng..."
            />
        </div>
    )
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-primary" />
            </div>
            <h3 className="font-semibold text-lg text-foreground mb-2">
                Trợ lý AI Y tế
            </h3>
            <p className="text-muted-foreground text-sm max-w-sm">
                Đặt câu hỏi bằng tiếng Việt về sức khỏe, thuốc, hoặc triệu chứng.
                AI sẽ phân tích và trả lời dựa trên hồ sơ bệnh án của bạn.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                    "Tôi bị đau đầu và mệt mỏi",
                    "Thuốc này có tác dụng phụ gì?",
                    "Huyết áp của tôi thế nào?",
                ].map((suggestion) => (
                    <button
                        key={suggestion}
                        className="px-3 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 transition-colors"
                    >
                        {suggestion}
                    </button>
                ))}
            </div>
        </div>
    )
}
