import { Badge } from "@/components/ui/badge"
import type { MedicalRecordAIAnalysis } from "@/types"

interface RecordAIAnalysisProps {
    analysis?: MedicalRecordAIAnalysis | string | null
}

interface RecordDoctorCommentProps {
    doctorComment?: string | null
}

function normalizeList(value: unknown, maxItems = 5): string[] {
    if (Array.isArray(value)) {
        return value
            .map((item) => String(item).trim())
            .filter(Boolean)
            .slice(0, maxItems)
    }
    if (typeof value === "string" && value.trim()) {
        return [value.trim()]
    }
    return []
}

function normalizeAnalysis(analysis?: MedicalRecordAIAnalysis | string | null): MedicalRecordAIAnalysis | null {
    if (!analysis) return null
    if (typeof analysis === "string") {
        const summary = analysis.trim()
        return summary ? { summary, status: "completed" } : null
    }
    return analysis
}

function getUrgencyBadgeVariant(urgency?: string): "outline" | "secondary" | "destructive" {
    if (urgency === "high") return "destructive"
    if (urgency === "medium") return "secondary"
    return "outline"
}

export function RecordDoctorComment({ doctorComment }: RecordDoctorCommentProps) {
    const normalizedDoctorComment =
        typeof doctorComment === "string" ? doctorComment.trim() : ""
    if (!normalizedDoctorComment) return null

    return (
        <div className="mt-3 rounded-lg border bg-background/80 p-3">
            <p className="text-sm font-semibold text-foreground">Nhận xét bác sĩ</p>
            <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
                {normalizedDoctorComment}
            </p>
        </div>
    )
}

export function RecordAIAnalysis({ analysis }: RecordAIAnalysisProps) {
    const parsed = normalizeAnalysis(analysis)
    if (!parsed) return null

    const summary = parsed && typeof parsed.summary === "string" ? parsed.summary.trim() : ""
    const keyFindings = parsed ? normalizeList(parsed.key_findings) : []
    const followUp = parsed ? normalizeList(parsed.recommended_follow_up) : []
    const limitations = parsed ? normalizeList(parsed.limitations) : []

    if (
        !summary
        && keyFindings.length === 0
        && followUp.length === 0
        && limitations.length === 0
    ) {
        return null
    }

    const urgency = parsed && typeof parsed.urgency === "string" ? parsed.urgency.toLowerCase() : undefined
    const urgencyLabel =
        urgency === "high" ? "Mức độ khẩn: Cao"
        : urgency === "medium" ? "Mức độ khẩn: Trung bình"
        : urgency === "low" ? "Mức độ khẩn: Thấp"
        : null

    return (
        <div className="mt-3 rounded-lg border bg-muted/30 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">Phân tích AI</p>
                {urgencyLabel && <Badge variant={getUrgencyBadgeVariant(urgency)}>{urgencyLabel}</Badge>}
            </div>

            {summary && (
                <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
                    {summary}
                </p>
            )}

            {keyFindings.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {keyFindings.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                    ))}
                </ul>
            )}

            {followUp.length > 0 && (
                <div className="mt-3 rounded-md border border-dashed bg-background/80 p-2">
                    <p className="text-xs font-medium text-foreground">Đề xuất theo dõi</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                        {followUp.map((item, index) => (
                            <li key={`${item}-${index}`}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {limitations.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                    <span className="font-medium">Giới hạn:</span> {limitations.join("; ")}
                </p>
            )}
        </div>
    )
}

