/**
 * Loading spinner component
 */
import { cn } from "@/lib/utils"

interface LoadingSpinnerProps {
    size?: "sm" | "md" | "lg"
    className?: string
}

const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 border-2",
    lg: "w-10 h-10 border-3",
}

export function LoadingSpinner({ size = "md", className }: LoadingSpinnerProps) {
    return (
        <div
            className={cn(
                "animate-spin rounded-full border-primary/30 border-t-primary",
                sizeClasses[size],
                className
            )}
        />
    )
}

interface LoadingOverlayProps {
    text?: string
}

export function LoadingOverlay({ text = "Đang tải..." }: LoadingOverlayProps) {
    return (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
            <LoadingSpinner size="lg" />
            <p className="text-sm text-muted-foreground">{text}</p>
        </div>
    )
}
