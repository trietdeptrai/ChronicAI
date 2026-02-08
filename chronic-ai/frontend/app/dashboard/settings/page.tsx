/**
 * Settings placeholder page
 */
"use client"

import { PageHeader } from "@/components/shared"
import { Card, CardContent } from "@/components/ui/card"
import { Settings } from "lucide-react"

export default function SettingsPage() {
    return (
        <div className="space-y-6">
            <PageHeader
                title="Cài đặt"
                description="Thiết lập tài khoản và tùy chọn thông báo"
            />
            <Card>
                <CardContent className="p-8 text-center">
                    <Settings className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-sm text-muted-foreground">
                        Trang cài đặt sẽ sớm có mặt.
                    </p>
                </CardContent>
            </Card>
        </div>
    )
}
