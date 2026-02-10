/**
 * Doctor orchestrator chat interface component.
 * Allows doctors to ask about any patient without pre-selection.
 */
"use client"

import { useRef, useEffect, useState } from "react"
import { useDoctorChat } from "@/lib/hooks"
import { MessageBubble } from "./message-bubble"
import { ChatInput } from "./chat-input"
import { StreamingProgress } from "./streaming-progress"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { X, Search, Users, Sparkles } from "lucide-react"

export function DoctorChatInterface() {
    const [showEnglish, setShowEnglish] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const {
        messages,
        isLoading,
        isStreaming,
        currentStage,
        currentProgress,
        mentionedPatients,
        error,
        sendMessage,
        clearMessages,
    } = useDoctorChat()

    // Scroll to bottom when messages or streaming state changes
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages.length, isStreaming, currentProgress])

    const handleSend = async (message: string, file?: File) => {
        let imagePath: string | undefined

        // Upload image first if provided
        if (file) {
            try {
                const { uploadChatImage } = await import("@/lib/api")
                const result = await uploadChatImage(file)
                imagePath = result.file_path
            } catch (uploadError) {
                console.error("Failed to upload image:", uploadError)
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
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div>
                        <h3 className="font-medium text-sm">Trợ lý Bác sĩ AI</h3>
                        <p className="text-xs text-muted-foreground">
                            Hỏi về bất kỳ bệnh nhân nào
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {/* Show mentioned patients */}
                    {mentionedPatients.length > 0 && (
                        <div className="flex items-center gap-1">
                            <Users className="w-3 h-3 text-muted-foreground" />
                            {mentionedPatients.slice(0, 3).map((patient) => (
                                <Badge
                                    key={patient.id}
                                    variant="secondary"
                                    className="text-xs"
                                >
                                    {patient.name}
                                </Badge>
                            ))}
                            {mentionedPatients.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                    +{mentionedPatients.length - 3}
                                </Badge>
                            )}
                        </div>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowEnglish(!showEnglish)}
                        className={showEnglish ? "text-primary" : ""}
                    >
                        <Search className="w-4 h-4 mr-1" />
                        <span className="text-xs">EN</span>
                    </Button>
                    {messages.length > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearMessages}
                            className="text-muted-foreground hover:text-destructive"
                        >
                            <X className="w-4 h-4" />
                        </Button>
                    )}
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                {messages.length === 0 && !isStreaming ? (
                    <DoctorEmptyState onSuggestionClick={handleSend} />
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
                                mode="doctor"
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
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <ChatInput
                onSend={handleSend}
                isLoading={isLoading}
                placeholder="Hỏi về bệnh nhân, ví dụ: 'Tình trạng của bệnh nhân Trần Thị Bình?'"
            />
        </div>
    )
}

interface DoctorEmptyStateProps {
    onSuggestionClick: (message: string) => void
}

function DoctorEmptyState({ onSuggestionClick }: DoctorEmptyStateProps) {
    const suggestions = [
        "Có bệnh nhân nào cần chú ý hôm nay không?",
        "Tình trạng của bệnh nhân Trần Thị Bình?",
        "Những bệnh nhân nào có chỉ số đường huyết cao?",
        "Tóm tắt các ca cấp cứu trong tuần",
    ]

    return (
        <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-6">
                <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <h3 className="font-semibold text-xl text-foreground mb-2">
                Trợ lý Bác sĩ AI
            </h3>
            <p className="text-muted-foreground text-sm max-w-md mb-8">
                Hỏi về bất kỳ bệnh nhân nào mà không cần chọn trước.
                AI sẽ tự động xác định bệnh nhân và truy xuất thông tin liên quan.
            </p>

            <div className="w-full max-w-lg">
                <p className="text-xs text-muted-foreground mb-3 font-medium uppercase tracking-wide">
                    Gợi ý câu hỏi
                </p>
                <div className="grid gap-2">
                    {suggestions.map((suggestion) => (
                        <button
                            key={suggestion}
                            onClick={() => onSuggestionClick(suggestion)}
                            className="w-full px-4 py-3 text-sm text-left rounded-xl bg-muted/50 hover:bg-muted transition-colors border border-transparent hover:border-border"
                        >
                            {suggestion}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}
