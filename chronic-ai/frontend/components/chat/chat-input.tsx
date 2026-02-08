/**
 * Chat input component with file upload
 */
"use client"

import { useState, useRef, type ChangeEvent, type KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/tooltip"
import { Send, Upload, X, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatInputProps {
    onSend: (message: string, file?: File) => void | Promise<void>
    isLoading?: boolean
    placeholder?: string
}

export function ChatInput({ onSend, isLoading = false, placeholder = "Nhập tin nhắn..." }: ChatInputProps) {
    const [message, setMessage] = useState("")
    const [file, setFile] = useState<File | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const handleSend = () => {
        if ((message.trim() || file) && !isLoading) {
            void onSend(message.trim(), file || undefined)
            setMessage("")
            setFile(null)
            textareaRef.current?.focus()
        }
    }

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0]
        if (selectedFile) {
            setFile(selectedFile)
        }
    }

    const removeFile = () => {
        setFile(null)
        if (fileInputRef.current) {
            fileInputRef.current.value = ""
        }
    }

    const isImage = file?.type.startsWith("image/")

    return (
        <div className="border-t border-border bg-background p-4">
            {/* File Preview */}
            {file && (
                <div className="mb-3 flex items-center gap-2 p-2 rounded-lg bg-muted">
                    <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
                        {isImage ? (
                            <Upload className="w-4 h-4 text-primary" />
                        ) : (
                            <FileText className="w-4 h-4 text-primary" />
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                            {(file.size / 1024).toFixed(1)} KB
                        </p>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={removeFile}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            )}

            {/* Input Area */}
            <div className="flex items-end gap-2">
                {/* File Upload Button */}
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="shrink-0"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isLoading}
                            >
                                <Upload className="h-5 w-5" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>Đính kèm tệp (PDF, hình ảnh)</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
                    className="hidden"
                    onChange={handleFileChange}
                />

                {/* Text Input */}
                <div className="flex-1 relative">
                    <Textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={placeholder}
                        disabled={isLoading}
                        className="min-h-[44px] max-h-32 resize-none pr-12"
                        rows={1}
                    />
                </div>

                {/* Send Button */}
                <Button
                    size="icon"
                    onClick={handleSend}
                    disabled={(!message.trim() && !file) || isLoading}
                    className={cn(
                        "shrink-0",
                        isLoading && "animate-pulse"
                    )}
                >
                    <Send className="h-5 w-5" />
                </Button>
            </div>

            {/* Help Text */}
            <p className="text-xs text-muted-foreground mt-2">
                Nhấn Enter để gửi, Shift+Enter để xuống dòng
            </p>
        </div>
    )
}
