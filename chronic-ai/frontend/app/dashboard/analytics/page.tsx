/**
 * Analytics placeholder page
 */
"use client"

import { PageHeader } from "@/components/shared"
import { Card, CardContent } from "@/components/ui/card"
import { BarChart3 } from "lucide-react"

export default function AnalyticsPage() {
    return (
        <div className="space-y-6">
            <PageHeader
                title="Báo cáo"
                description="Theo dõi xu hướng sức khỏe và hiệu quả chăm sóc"
            />
            <Card>
                <CardContent className="p-8 text-center">
                    <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-sm text-muted-foreground">
                        Dashboard phân tích đang được phát triển.
                    </p>
                </CardContent>
            </Card>
        </div>
    )
}
