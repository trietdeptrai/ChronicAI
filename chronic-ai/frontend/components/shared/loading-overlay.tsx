interface LoadingOverlayProps {
    text?: string
}

export function LoadingOverlay({ text = "Đang tải..." }: LoadingOverlayProps) {
    return (
        <div className="flex min-h-[280px] items-center justify-center">
            <p className="text-sm text-muted-foreground">{text}</p>
        </div>
    )
}
