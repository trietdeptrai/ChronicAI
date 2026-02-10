import type { ReactNode } from "react"

interface PageHeaderProps {
    title: string
    description?: string
    actions?: ReactNode
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
    return (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
                <h1 className="text-2xl font-bold text-[#1e2939]">{title}</h1>
                {description && <p className="text-sm text-[#4a5565]">{description}</p>}
            </div>
            {actions && <div>{actions}</div>}
        </div>
    )
}
