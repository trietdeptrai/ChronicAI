import { Badge } from "@/components/ui/badge"
import { useDashboardLanguage, type DashboardLanguage } from "@/contexts"
import type { MedicalRecordAIAnalysis } from "@/types"

interface RecordAIAnalysisProps {
    analysis?: MedicalRecordAIAnalysis | string | null
}

interface RecordDoctorCommentProps {
    doctorComment?: string | null
}

interface PredictionScoreRow {
    class: string
    description?: string
    score: number
}

const UI_TEXT: Record<
    DashboardLanguage,
    {
        doctorComment: string
        aiAnalysis: string
        urgencyHigh: string
        urgencyMedium: string
        urgencyLow: string
        recommendedFollowUp: string
        ecgScores: string
        limitations: string
    }
> = {
    vi: {
        doctorComment: "Nhận xét bác sĩ",
        aiAnalysis: "Phân tích AI",
        urgencyHigh: "Mức độ khẩn: Cao",
        urgencyMedium: "Mức độ khẩn: Trung bình",
        urgencyLow: "Mức độ khẩn: Thấp",
        recommendedFollowUp: "Đề xuất theo dõi",
        ecgScores: "Điểm dự đoán ECG",
        limitations: "Giới hạn",
    },
    en: {
        doctorComment: "Doctor Comment",
        aiAnalysis: "AI Analysis",
        urgencyHigh: "Urgency: High",
        urgencyMedium: "Urgency: Medium",
        urgencyLow: "Urgency: Low",
        recommendedFollowUp: "Recommended Follow-up",
        ecgScores: "ECG classifier scores",
        limitations: "Limitations",
    },
}

const ECG_CLASS_DESCRIPTION_MAP: Record<DashboardLanguage, Record<string, string>> = {
    vi: {
        NORM: "ECG bình thường",
        MI: "Nhồi máu cơ tim",
        STTC: "Biến đổi ST/T",
        CD: "Rối loạn dẫn truyền",
        HYP: "Phì đại",
    },
    en: {
        NORM: "Normal ECG",
        MI: "Myocardial Infarction",
        STTC: "ST/T Change",
        CD: "Conduction Disturbance",
        HYP: "Hypertrophy",
    },
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

function normalizePredictionScores(
    analysis: MedicalRecordAIAnalysis,
    language: DashboardLanguage,
): PredictionScoreRow[] {
    const rows: PredictionScoreRow[] = []

    const withDescription = (label: string, description: string | undefined): string | undefined => {
        const fallback = ECG_CLASS_DESCRIPTION_MAP[language][label] || ECG_CLASS_DESCRIPTION_MAP.en[label]
        const cleaned = typeof description === "string" ? description.trim() : ""
        return fallback || cleaned || undefined
    }

    const directScores = analysis.prediction_scores
    if (Array.isArray(directScores)) {
        for (const item of directScores) {
            const label = typeof item.class === "string" ? item.class.trim() : ""
            const numericScore = Number(item.score)
            if (!label || !Number.isFinite(numericScore)) continue
            rows.push({
                class: label,
                description: withDescription(label, item.description),
                score: numericScore,
            })
        }
    }

    if (rows.length > 0) {
        return rows.sort((a, b) => b.score - a.score)
    }

    const ecgClassifier = (
        analysis.ecg_classifier && typeof analysis.ecg_classifier === "object"
            ? analysis.ecg_classifier as Record<string, unknown>
            : null
    )
    if (!ecgClassifier) return []

    const classes = Array.isArray(ecgClassifier.classes) ? ecgClassifier.classes : []
    const scores = Array.isArray(ecgClassifier.scores) ? ecgClassifier.scores : []

    if (classes.length > 0 && scores.length > 0) {
        classes.forEach((labelValue, index) => {
            const label = typeof labelValue === "string" ? labelValue.trim() : ""
            const numericScore = Number(scores[index])
            if (!label || !Number.isFinite(numericScore)) return
            rows.push({
                class: label,
                description: withDescription(label, undefined),
                score: numericScore,
            })
        })
    } else {
        const scoreMap = (
            ecgClassifier.scores_by_class && typeof ecgClassifier.scores_by_class === "object"
                ? ecgClassifier.scores_by_class as Record<string, unknown>
                : {}
        )
        Object.entries(scoreMap).forEach(([label, scoreValue]) => {
            const numericScore = Number(scoreValue)
            if (!Number.isFinite(numericScore)) return
            rows.push({
                class: label,
                description: withDescription(label, undefined),
                score: numericScore,
            })
        })
    }

    return rows.sort((a, b) => b.score - a.score)
}

function getUrgencyBadgeVariant(urgency?: string): "outline" | "secondary" | "destructive" {
    if (urgency === "high") return "destructive"
    if (urgency === "medium") return "secondary"
    return "outline"
}

export function RecordDoctorComment({ doctorComment }: RecordDoctorCommentProps) {
    const { language } = useDashboardLanguage()
    const t = UI_TEXT[language]
    const normalizedDoctorComment =
        typeof doctorComment === "string" ? doctorComment.trim() : ""
    if (!normalizedDoctorComment) return null

    return (
        <div className="mt-3 rounded-lg border bg-background/80 p-3">
            <p className="text-sm font-semibold text-foreground">{t.doctorComment}</p>
            <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
                {normalizedDoctorComment}
            </p>
        </div>
    )
}

export function RecordAIAnalysis({ analysis }: RecordAIAnalysisProps) {
    const { language } = useDashboardLanguage()
    const t = UI_TEXT[language]
    const parsed = normalizeAnalysis(analysis)
    if (!parsed) return null

    const summary = parsed && typeof parsed.summary === "string" ? parsed.summary.trim() : ""
    const keyFindings = parsed ? normalizeList(parsed.key_findings) : []
    const followUp = parsed ? normalizeList(parsed.recommended_follow_up) : []
    const limitations = parsed ? normalizeList(parsed.limitations) : []
    const predictionScores = parsed ? normalizePredictionScores(parsed, language) : []

    if (
        !summary
        && keyFindings.length === 0
        && followUp.length === 0
        && limitations.length === 0
        && predictionScores.length === 0
    ) {
        return null
    }

    const urgency = parsed && typeof parsed.urgency === "string" ? parsed.urgency.toLowerCase() : undefined
    const urgencyLabel =
        urgency === "high" ? t.urgencyHigh
        : urgency === "medium" ? t.urgencyMedium
        : urgency === "low" ? t.urgencyLow
        : null

    return (
        <div className="mt-3 rounded-lg border bg-muted/30 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{t.aiAnalysis}</p>
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
                    <p className="text-xs font-medium text-foreground">{t.recommendedFollowUp}</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                        {followUp.map((item, index) => (
                            <li key={`${item}-${index}`}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {predictionScores.length > 0 && (
                <div className="mt-3 rounded-md border border-dashed bg-background/80 p-2">
                    <p className="text-xs font-medium text-foreground">{t.ecgScores}</p>
                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {predictionScores.map((row) => (
                            <li key={row.class} className="flex items-start justify-between gap-3">
                                <span>
                                    <span className="font-medium text-foreground">{row.class}</span>
                                    {row.description ? ` - ${row.description}` : ""}
                                </span>
                                <span className="font-medium text-foreground">
                                    {(row.score * 100).toFixed(1)}%
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {limitations.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                    <span className="font-medium">{t.limitations}:</span> {limitations.join("; ")}
                </p>
            )}
        </div>
    )
}
