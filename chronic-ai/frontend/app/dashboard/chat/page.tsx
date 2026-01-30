/**
 * Chat page
 */
"use client"

import { useState } from "react"
import { useAuth } from "@/contexts"
import { usePatients } from "@/lib/hooks"
import { PageHeader } from "@/components/shared"
import { ChatInterface } from "@/components/chat"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Search, User, MessageSquare } from "lucide-react"

export default function ChatPage() {
    const { role, user } = useAuth()
    const isDoctor = role === "doctor"

    // For doctors, show patient selector. For patients, use their own ID from auth
    const [selectedPatientId, setSelectedPatientId] = useState<string | null>(
        isDoctor ? null : (user?.id || null)
    )
    const [selectedPatientName, setSelectedPatientName] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState("")

    // Only fetch patients for doctors
    const { data: patientsData, isLoading } = usePatients(
        isDoctor ? { search: searchQuery, pageSize: 50 } : { pageSize: 0 }
    )

    const handleSelectPatient = (patientId: string, patientName: string) => {
        setSelectedPatientId(patientId)
        setSelectedPatientName(patientName)
    }

    // For patients, show chat directly
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

    // For doctors, show patient selector + chat
    return (
        <div className="h-[calc(100vh-theme(spacing.16))]">
            <PageHeader
                title="Trò chuyện AI"
                description="Tư vấn với hỗ trợ AI y tế"
            />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100%-80px)]">
                {/* Patient Selector */}
                <Card className="lg:col-span-1 flex flex-col">
                    <div className="p-4 border-b border-border">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Tìm bệnh nhân..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9"
                            />
                        </div>
                    </div>

                    <ScrollArea className="flex-1">
                        <div className="p-2 space-y-1">
                            {isLoading ? (
                                <p className="text-sm text-muted-foreground p-4 text-center">
                                    Đang tải...
                                </p>
                            ) : patientsData?.patients.length === 0 ? (
                                <p className="text-sm text-muted-foreground p-4 text-center">
                                    Không tìm thấy bệnh nhân
                                </p>
                            ) : (
                                patientsData?.patients.map((patient) => (
                                    <button
                                        key={patient.id}
                                        onClick={() => handleSelectPatient(patient.id, patient.full_name)}
                                        className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-colors ${selectedPatientId === patient.id
                                                ? "bg-primary/10 text-primary"
                                                : "hover:bg-muted"
                                            }`}
                                    >
                                        <Avatar className="h-8 w-8">
                                            <AvatarFallback className="text-xs">
                                                {patient.full_name.slice(0, 2).toUpperCase()}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">
                                                {patient.full_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {patient.primary_diagnosis || "Chưa có chẩn đoán"}
                                            </p>
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </Card>

                {/* Chat Interface */}
                <Card className="lg:col-span-3 flex flex-col">
                    {selectedPatientId ? (
                        <ChatInterface
                            patientId={selectedPatientId}
                            patientName={selectedPatientName || undefined}
                        />
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
                                <MessageSquare className="w-8 h-8 text-muted-foreground/50" />
                            </div>
                            <h3 className="font-medium text-foreground mb-2">
                                Chọn bệnh nhân
                            </h3>
                            <p className="text-sm text-muted-foreground max-w-sm">
                                Chọn bệnh nhân từ danh sách bên trái để bắt đầu tư vấn với hỗ trợ AI
                            </p>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    )
}
