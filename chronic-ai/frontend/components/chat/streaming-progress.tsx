/**
 * Progress indicator for streaming chat
 */
import { cn } from "@/lib/utils"
import { Languages, Search, Brain, CheckCircle } from "lucide-react"
import type { ChatStreamUpdate } from "@/types"

interface StreamingProgressProps {
    stage?: ChatStreamUpdate["stage"]
    progress: number
    message?: string
}

const stages = [
    { id: "translating_input", label: "Dịch sang tiếng Anh", icon: Languages },
    { id: "retrieving_context", label: "Tìm kiếm hồ sơ", icon: Search },
    { id: "medical_reasoning", label: "Phân tích y tế", icon: Brain },
    { id: "translating_output", label: "Dịch sang tiếng Việt", icon: Languages },
]

export function StreamingProgress({ stage, progress, message }: StreamingProgressProps) {
    if (!stage || stage === "complete") return null

    const currentStageIndex = stages.findIndex(s => s.id === stage)

    return (
        <div className="p-4 bg-muted/50 rounded-lg border border-border/50 animate-in fade-in duration-300">
            <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span className="text-sm font-medium text-foreground">
                    Đang xử lý...
                </span>
            </div>

            {/* Progress Steps */}
            <div className="space-y-2">
                {stages.map((s, index) => {
                    const isActive = s.id === stage
                    const isCompleted = index < currentStageIndex
                    const isPending = index > currentStageIndex

                    return (
                        <div
                            key={s.id}
                            className={cn(
                                "flex items-center gap-3 py-1.5 px-2 rounded-md transition-colors",
                                isActive && "bg-primary/10",
                                isCompleted && "opacity-60"
                            )}
                        >
                            <div
                                className={cn(
                                    "w-6 h-6 rounded-full flex items-center justify-center",
                                    isActive && "bg-primary text-primary-foreground",
                                    isCompleted && "bg-green-500 text-white",
                                    isPending && "bg-muted-foreground/20 text-muted-foreground"
                                )}
                            >
                                {isCompleted ? (
                                    <CheckCircle className="w-3.5 h-3.5" />
                                ) : (
                                    <s.icon className={cn("w-3.5 h-3.5", isActive && "animate-pulse")} />
                                )}
                            </div>
                            <span
                                className={cn(
                                    "text-sm",
                                    isActive && "font-medium text-foreground",
                                    isCompleted && "text-muted-foreground",
                                    isPending && "text-muted-foreground/60"
                                )}
                            >
                                {s.label}
                            </span>
                        </div>
                    )
                })}
            </div>

            {/* Progress Bar */}
            <div className="mt-4">
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary transition-all duration-500 ease-out rounded-full"
                        style={{ width: `${progress * 100}%` }}
                    />
                </div>
                <p className="text-xs text-muted-foreground mt-1.5">
                    {Math.round(progress * 100)}% hoàn thành
                </p>
            </div>
        </div>
    )
}
