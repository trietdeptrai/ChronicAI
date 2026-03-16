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
        keyFindings: string
        clinicalSignificance: string
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
        keyFindings: "Điểm chính",
        clinicalSignificance: "Ý nghĩa lâm sàng",
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
        keyFindings: "Key findings",
        clinicalSignificance: "Clinical significance",
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

function normalizeText(value: unknown): string {
    if (typeof value !== "string") return ""
    return value
        .replace(/\r\n?/g, "\n")
        .replace(/\u00a0/g, " ")
        .trim()
}

function stripMarkdownCodeFence(value: string): string {
    const trimmed = normalizeText(value)
    if (!trimmed.startsWith("```")) return trimmed

    return trimmed
        .replace(/^```[a-zA-Z0-9_-]*\s*/, "")
        .replace(/\s*```$/, "")
        .trim()
}

function extractJsonObject(value: string): Record<string, unknown> | null {
    const cleaned = stripMarkdownCodeFence(value)
    if (!cleaned) return null

    const candidates = [cleaned]
    const objectStart = cleaned.indexOf("{")
    const objectEnd = cleaned.lastIndexOf("}")
    if (objectStart !== -1 && objectEnd > objectStart) {
        candidates.push(cleaned.slice(objectStart, objectEnd + 1))
    }

    for (const candidate of candidates) {
        try {
            const parsed = JSON.parse(candidate)
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
                return parsed as Record<string, unknown>
            }
        } catch {
            continue
        }
    }

    return null
}

function hasStructuredAnalysisFields(value: Record<string, unknown>): boolean {
    return [
        "summary",
        "key_findings",
        "clinical_significance",
        "recommended_follow_up",
        "prediction_scores",
        "ecg_classifier",
    ].some((key) => key in value)
}

function normalizeAnalysisObject(value: Record<string, unknown>): MedicalRecordAIAnalysis | null {
    const rawSummary = normalizeText(value.summary)
    const parsedSummaryPayload = rawSummary ? extractJsonObject(rawSummary) : null
    const source =
        parsedSummaryPayload && hasStructuredAnalysisFields(parsedSummaryPayload)
            ? { ...value, ...parsedSummaryPayload }
            : value

    const summary = stripMarkdownCodeFence(String(source.summary ?? ""))
    const clinicalSignificance = stripMarkdownCodeFence(String(source.clinical_significance ?? ""))

    return {
        ...source,
        status:
            source.status === "completed" || source.status === "skipped" || source.status === "error"
                ? source.status
                : undefined,
        summary: summary || undefined,
        key_findings: normalizeList(source.key_findings),
        clinical_significance: clinicalSignificance || undefined,
        recommended_follow_up: normalizeList(source.recommended_follow_up),
        limitations: normalizeList(source.limitations),
        urgency:
            source.urgency === "low" || source.urgency === "medium" || source.urgency === "high"
                ? source.urgency
                : undefined,
        confidence:
            source.confidence === "low" || source.confidence === "medium" || source.confidence === "high"
                ? source.confidence
                : undefined,
    }
}

function normalizeAnalysis(analysis?: MedicalRecordAIAnalysis | string | null): MedicalRecordAIAnalysis | null {
    if (!analysis) return null

    if (typeof analysis === "string") {
        const parsed = extractJsonObject(analysis)
        if (parsed && hasStructuredAnalysisFields(parsed)) {
            return normalizeAnalysisObject(parsed)
        }

        const summary = stripMarkdownCodeFence(analysis)
        return summary ? { summary, status: "completed" } : null
    }

    return normalizeAnalysisObject(analysis)
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

function isProbabilityScore(score: number): boolean {
    return score >= 0 && score <= 1
}

function formatPredictionScore(score: number): string {
    if (isProbabilityScore(score)) {
        return `${(score * 100).toFixed(1)}%`
    }

    if (Math.abs(score) >= 100) {
        return score.toFixed(0)
    }

    if (Math.abs(score) >= 10) {
        return score.toFixed(1)
    }

    return score.toFixed(3).replace(/\.?0+$/, "")
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
    const clinicalSignificance =
        parsed && typeof parsed.clinical_significance === "string"
            ? parsed.clinical_significance.trim()
            : ""
    const followUp = parsed ? normalizeList(parsed.recommended_follow_up) : []
    const limitations = parsed ? normalizeList(parsed.limitations) : []
    const predictionScores = parsed ? normalizePredictionScores(parsed, language) : []

    if (
        !summary
        && keyFindings.length === 0
        && !clinicalSignificance
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
        <div className="mt-3 rounded-xl border bg-muted/30 p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{t.aiAnalysis}</p>
                {urgencyLabel && <Badge variant={getUrgencyBadgeVariant(urgency)}>{urgencyLabel}</Badge>}
            </div>

            {summary && (
                <p className="mt-3 text-sm leading-6 text-muted-foreground whitespace-pre-line">
                    {summary}
                </p>
            )}

            {keyFindings.length > 0 && (
                <div className="mt-4 rounded-lg border bg-background/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        {t.keyFindings}
                    </p>
                    <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-muted-foreground">
                        {keyFindings.map((item, index) => (
                            <li key={`${item}-${index}`}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {clinicalSignificance && (
                <div className="mt-4 rounded-lg border bg-background/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        {t.clinicalSignificance}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground whitespace-pre-line">
                        {clinicalSignificance}
                    </p>
                </div>
            )}

            {followUp.length > 0 && (
                <div className="mt-4 rounded-lg border border-dashed bg-background/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        {t.recommendedFollowUp}
                    </p>
                    <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-muted-foreground">
                        {followUp.map((item, index) => (
                            <li key={`${item}-${index}`}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {predictionScores.length > 0 && (
                <div className="mt-4 rounded-lg border border-dashed bg-background/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        {t.ecgScores}
                    </p>
                    <ul className="mt-3 space-y-2">
                        {predictionScores.map((row) => (
                            <li
                                key={row.class}
                                className="flex items-center justify-between gap-4 rounded-md border border-border/60 px-3 py-2"
                            >
                                <span className="min-w-0">
                                    <span className="font-medium text-foreground">{row.class}</span>
                                    {row.description ? (
                                        <span className="block text-xs leading-5 text-muted-foreground">
                                            {row.description}
                                        </span>
                                    ) : null}
                                </span>
                                <span className="shrink-0 font-semibold text-foreground">
                                    {formatPredictionScore(row.score)}
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {limitations.length > 0 && (
                <p className="mt-4 text-xs leading-5 text-muted-foreground">
                    <span className="font-medium">{t.limitations}:</span> {limitations.join("; ")}
                </p>
            )}
        </div>
    )
}
