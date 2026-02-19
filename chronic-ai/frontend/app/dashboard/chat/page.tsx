/**
 * Chat page
 */
"use client"

import { useAuth } from "@/contexts"
import { PageHeader } from "@/components/shared"
import { ChatInterface, DoctorChatInterface } from "@/components/chat"
import { Card } from "@/components/ui/card"

export default function ChatPage() {
    const { role, user } = useAuth()
    const isDoctor = role === "doctor"

    // For patients, show patient-specific chat with their own ID
    if (!isDoctor && user?.id) {
        return (
            <div className="h-[calc(100vh-theme(spacing.16))]">
                <Card className="h-full">
                    <ChatInterface
                        patientId={user.id}
                        patientName="Tài khoản của tôi"
                    />
                </Card>
            </div>
        )
    }

    // For doctors, show the orchestrator chat (no patient pre-selection needed)
    return (
        <div className="h-[calc(100vh-theme(spacing.16))]">
            <PageHeader
                title="Trợ lý Bác sĩ AI"
                description="Hỏi về bất kỳ bệnh nhân nào - không cần chọn trước"
            />

            <Card className="h-[calc(100%-80px)]">
                <DoctorChatInterface doctorId={user?.id} />
            </Card>
        </div>
    )
}
