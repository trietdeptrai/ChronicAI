/**
 * Message bubble component
 */
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/types"
import { User, Bot, Copy, Check } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import ReactMarkdown from "react-markdown"

interface MessageBubbleProps {
    message: ChatMessage
    showEnglish?: boolean
}

export function MessageBubble({ message, showEnglish = false }: MessageBubbleProps) {
    const [copied, setCopied] = useState(false)
    const isUser = message.role === "user"

    const attachments = message.attachments || []

    const handleCopy = async () => {
        await navigator.clipboard.writeText(message.content)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div
            className={cn(
                "flex gap-3 group",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            {/* Avatar */}
            <div
                className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                    isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-gradient-to-br from-chart-2 to-chart-2/80 text-white"
                )}
            >
                {isUser ? (
                    <User className="w-4 h-4" />
                ) : (
                    <Bot className="w-4 h-4" />
                )}
            </div>

            {/* Message Content */}
            <div
                className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-2.5",
                    isUser
                        ? "bg-primary text-primary-foreground rounded-tr-sm"
                        : "bg-muted text-foreground rounded-tl-sm"
                )}
            >
                <div className="text-sm leading-relaxed markdown-content">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {/* Attachments */}
                {attachments.length > 0 && (
                    <div className="mt-3 space-y-2">
                        {attachments.map((attachment, index) => {
                            if (attachment.type !== "image") return null
                            const captionParts = [
                                attachment.title,
                                attachment.record_type,
                                attachment.patient_name,
                                attachment.created_at ? formatDate(attachment.created_at) : undefined,
                            ].filter(Boolean)
                            const caption = captionParts.join(" • ")

                            return (
                                <div key={`${attachment.url}-${index}`} className="space-y-1">
                                    <img
                                        src={attachment.url}
                                        alt={attachment.title || "Medical image"}
                                        className="w-full max-w-[360px] rounded-lg border border-border/60 object-contain"
                                        loading="lazy"
                                    />
                                    {caption && (
                                        <p
                                            className={cn(
                                                "text-xs",
                                                isUser ? "text-primary-foreground/70" : "text-muted-foreground"
                                            )}
                                        >
                                            {caption}
                                        </p>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                )}

                {/* Show English translation if available */}
                {showEnglish && message.content_en && (
                    <div className="mt-2 pt-2 border-t border-current/10">
                        <p className="text-xs opacity-70 italic">
                            {message.content_en}
                        </p>
                    </div>
                )}

                {/* Timestamp */}
                <p
                    className={cn(
                        "text-xs mt-1",
                        isUser ? "text-primary-foreground/60" : "text-muted-foreground"
                    )}
                >
                    {formatTime(message.timestamp)}
                </p>
            </div>

            {/* Copy button - only for assistant messages */}
            {!isUser && (
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={handleCopy}
                >
                    {copied ? (
                        <Check className="h-3.5 w-3.5 text-green-500" />
                    ) : (
                        <Copy className="h-3.5 w-3.5" />
                    )}
                </Button>
            )}
        </div>
    )
}

function formatTime(timestamp: string): string {
    return new Date(timestamp).toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
    })
}

function formatDate(timestamp: string): string {
    const date = new Date(timestamp)
    if (Number.isNaN(date.getTime())) {
        return timestamp
    }
    return date.toLocaleDateString("vi-VN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    })
}
