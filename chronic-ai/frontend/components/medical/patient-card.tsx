/**
 * Patient card component
 */
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Calendar, Phone, AlertCircle } from "lucide-react"
import type { Patient } from "@/types"

interface PatientCardProps {
    patient: Patient
    onClick?: () => void
}

export function PatientCard({ patient, onClick }: PatientCardProps) {
    const age = calculateAge(patient.date_of_birth)
    const initials = getInitials(patient.full_name)

    const priorityStyles = {
        urgent: "priority-urgent",
        high: "priority-high",
        medium: "priority-medium",
        low: "priority-low",
    }

    const priorityLabels = {
        urgent: "Khẩn cấp",
        high: "Ưu tiên cao",
        medium: "Trung bình",
        low: "Thấp",
    }

    const genderLabels = {
        male: "Nam",
        female: "Nữ",
        other: "Khác",
    }

    return (
        <Card
            className={cn(
                "cursor-pointer transition-all hover:shadow-md hover:border-primary/30",
                patient.triage_priority === "urgent" && "border-destructive/30"
            )}
            onClick={onClick}
        >
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <Avatar className="h-12 w-12">
                        {patient.profile_photo_url && (
                            <AvatarImage
                                src={patient.profile_photo_url}
                                alt={patient.full_name}
                            />
                        )}
                        <AvatarFallback className="bg-primary/10 text-primary font-medium">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-foreground truncate">
                                {patient.full_name}
                            </h3>
                            {patient.triage_priority && patient.triage_priority !== "low" && (
                                <Badge
                                    variant="outline"
                                    className={cn("text-xs", priorityStyles[patient.triage_priority])}
                                >
                                    {patient.triage_priority === "urgent" && (
                                        <AlertCircle className="w-3 h-3 mr-1" />
                                    )}
                                    {priorityLabels[patient.triage_priority]}
                                </Badge>
                            )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                            <span>{age} tuổi</span>
                            <span>•</span>
                            <span>{genderLabels[patient.gender]}</span>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
                {/* Chronic Conditions */}
                {patient.chronic_conditions && patient.chronic_conditions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {patient.chronic_conditions.slice(0, 3).map((condition, index) => (
                            <Badge key={index} variant="secondary" className="text-xs">
                                {condition.name}
                            </Badge>
                        ))}
                        {patient.chronic_conditions.length > 3 && (
                            <Badge variant="secondary" className="text-xs">
                                +{patient.chronic_conditions.length - 3}
                            </Badge>
                        )}
                    </div>
                )}

                {/* Contact & Last Visit */}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        <span>{patient.phone_primary}</span>
                    </div>
                    {patient.last_checkup_date && (
                        <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span>Khám: {formatDate(patient.last_checkup_date)}</span>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

function calculateAge(dateOfBirth: string): number {
    const today = new Date()
    const birthDate = new Date(dateOfBirth)
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age--
    }
    return age
}

function getInitials(name: string): string {
    return name
        .split(" ")
        .map(word => word[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
}

function formatDate(dateString: string): string {
    const date = new Date(dateString)
    return date.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    })
}
