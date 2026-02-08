/**
 * Chat placeholder route for sidebar navigation
 */
"use client"

import Link from "next/link"
import { useAuth } from "@/contexts"
import { PageHeader } from "@/components/shared"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MessageSquare, ArrowRight } from "lucide-react"

export default function ChatPage() {
    const { role } = useAuth()

    return (
        <div className="space-y-6">
            <PageHeader
                title="AI Chat"
                description="Điểm vào hội thoại AI được kết nối backend"
            />

            <Card>
                <CardContent className="p-8 text-center">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-sm text-muted-foreground mb-4">
                        {role === "doctor"
                            ? "Chọn một bệnh nhân để bắt đầu trao đổi AI dựa trên hồ sơ."
                            : "Bạn có thể mở hồ sơ để xem lịch sử và trao đổi liên quan điều trị."}
                    </p>
                    <Button asChild variant="outline">
                        <Link href={role === "doctor" ? "/dashboard/patients" : "/dashboard/records"}>
                            {role === "doctor" ? "Đến danh sách bệnh nhân" : "Đến hồ sơ của tôi"}
                            <ArrowRight className="h-4 w-4 ml-1" />
                        </Link>
                    </Button>
                </CardContent>
            </Card>
        </div>
    )
}
