/**
 * Progress indicator for streaming chat
 */
import { cn } from "@/lib/utils"
import { Search, Bot, CheckCircle2, Users } from "lucide-react"
import type { ChatStreamUpdate, DoctorChatStreamUpdate } from "@/types"

type StageType = ChatStreamUpdate["stage"] | DoctorChatStreamUpdate["stage"]
type ProgressMode = "patient" | "doctor"

interface StreamingProgressProps {
    stage?: StageType
    progress: number
    mode?: ProgressMode
}

// Patient-specific chat stages
const patientStages = [
    { id: "verifying_input", label: "Phân tích câu hỏi", icon: Search },
    { id: "retrieving_context", label: "Tìm kiếm hồ sơ", icon: Search },
    { id: "triaged", label: "Đánh giá mức độ khẩn cấp", icon: Search },
    { id: "medical_reasoning", label: "Phân tích y tế", icon: Bot },
    { id: "formatting_output", label: "Hoàn thiện phản hồi", icon: Search },
]

// Doctor orchestrator stages
const doctorStages = [
    { id: "translating_input", label: "Phân tích câu hỏi", icon: Search },
    { id: "verifying_input", label: "Kiểm tra độ rõ ràng", icon: Search },
    { id: "extracting_patients", label: "Xác định bệnh nhân", icon: Users },
    { id: "resolving_patients", label: "Tìm hồ sơ bệnh nhân", icon: Search },
    { id: "retrieving_context", label: "Tổng hợp thông tin", icon: Search },
    { id: "medical_reasoning", label: "Phân tích y tế", icon: Bot },
    { id: "safety_check", label: "Kiểm tra an toàn", icon: Search },
    { id: "formatting_output", label: "Định dạng kết quả", icon: Bot },
    { id: "translating_output", label: "Hoàn thiện phản hồi", icon: Search },
]

const doctorStageAlias: Partial<Record<StageType, string>> = {
    starting: "translating_input",
    translated_input: "translating_input",
    verified_input: "verifying_input",
    extracted_patients: "extracting_patients",
    resolved_patients: "resolving_patients",
    retrieved_context: "retrieving_context",
    reasoned: "medical_reasoning",
    safety_checked: "safety_check",
    formatted: "formatting_output",
    hitl_required: "safety_check",
}

const doctorStageIds = new Set(doctorStages.map((stageItem) => stageItem.id))
const patientStageAlias: Partial<Record<StageType, string>> = {
    starting: "verifying_input",
    translated_input: "verifying_input",
    verified_input: "verifying_input",
    retrieved_history: "retrieving_context",
    escalated: "medical_reasoning",
    reasoned: "medical_reasoning",
    formatted: "formatting_output",
}

export function StreamingProgress({ stage, progress, mode }: StreamingProgressProps) {
    if (!stage || stage === "complete") return null

    const inferredMode: ProgressMode = doctorStageIds.has(stage) || stage in doctorStageAlias
        ? "doctor"
        : "patient"
    const effectiveMode = mode || inferredMode
    const stages = effectiveMode === "doctor" ? doctorStages : patientStages

    const normalizedStage = effectiveMode === "doctor"
        ? (doctorStageAlias[stage] || stage)
        : (patientStageAlias[stage] || stage)
    const currentStageIndex = stages.findIndex(s => s.id === normalizedStage)

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
                    const isActive = s.id === normalizedStage
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
                                    <CheckCircle2 className="w-3.5 h-3.5" />
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
