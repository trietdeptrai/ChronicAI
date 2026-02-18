import { Progress } from "@/components/progress"

interface UploadProgressOverlayProps {
    open: boolean
    title: string
    stage: string
    progress: number
}

export function UploadProgressOverlay({
    open,
    title,
    stage,
    progress,
}: UploadProgressOverlayProps) {
    if (!open) return null

    const safeProgress = Math.max(0, Math.min(progress, 100))

    return (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-background/70 p-4">
            <div className="w-full max-w-md rounded-xl border bg-card p-5 shadow-xl">
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-2 text-sm text-muted-foreground">{stage}</p>

                <div className="mt-4 space-y-2">
                    <Progress value={safeProgress} className="h-2.5" />
                    <p className="text-right text-xs font-medium text-muted-foreground">
                        {Math.round(safeProgress)}%
                    </p>
                </div>
            </div>
        </div>
    )
}
