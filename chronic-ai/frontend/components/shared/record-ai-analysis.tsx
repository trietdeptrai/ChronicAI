import { Badge } from "@/components/ui/badge"
import type { MedicalRecordAIAnalysis } from "@/types"

interface RecordAIAnalysisProps {
    analysis?: MedicalRecordAIAnalysis | string | null
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

export function RecordAIAnalysis({ analysis }: RecordAIAnalysisProps) {
    const parsed = normalizeAnalysis(analysis)
    if (!parsed) return null

    const summary = typeof parsed.summary === "string" ? parsed.summary.trim() : ""
    const keyFindings = normalizeList(parsed.key_findings)
    const followUp = normalizeList(parsed.recommended_follow_up)
    const limitations = normalizeList(parsed.limitations)

    if (!summary && keyFindings.length === 0 && followUp.length === 0 && limitations.length === 0) {
        return null
    }

    const urgency = typeof parsed.urgency === "string" ? parsed.urgency.toLowerCase() : undefined
    const urgencyLabel =
        urgency === "high" ? "Urgency: High"
        : urgency === "medium" ? "Urgency: Medium"
        : urgency === "low" ? "Urgency: Low"
        : null

    return (
        <div className="mt-3 rounded-lg border bg-muted/30 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">AI analysis</p>
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
                    <p className="text-xs font-medium text-foreground">Suggested follow-up</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                        {followUp.map((item, index) => (
                            <li key={`${item}-${index}`}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {limitations.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                    <span className="font-medium">Limitations:</span> {limitations.join("; ")}
                </p>
            )}
        </div>
    )
}

