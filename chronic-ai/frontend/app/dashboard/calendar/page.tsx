/**
 * Calendar placeholder page
 */
"use client"

import { PageHeader } from "@/components/shared"
import { Card, CardContent } from "@/components/ui/card"
import { Calendar } from "lucide-react"

export default function CalendarPage() {
    return (
        <div className="space-y-6">
            <PageHeader
                title="Lịch hẹn"
                description="Quản lý lịch tái khám và nhắc nhở"
            />
            <Card>
                <CardContent className="p-8 text-center">
                    <Calendar className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-sm text-muted-foreground">
                        Tính năng lịch hẹn đang được hoàn thiện.
                    </p>
                </CardContent>
            </Card>
        </div>
    )
}
