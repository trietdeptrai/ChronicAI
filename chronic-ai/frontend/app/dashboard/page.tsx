"use client"

import Link from "next/link"
import { useMemo, useState, type ReactNode } from "react"
import { useAuth } from "@/contexts"
import { useDebounce, useDashboardStats, usePatient, usePatientRecords, usePatients } from "@/lib/hooks"
import { Button } from "@/components/button"
import { Input } from "@/components/input"
import { Badge } from "@/components/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/card"
import { User, Search, FileText, Activity, ImageIcon, ArrowRight } from "lucide-react"

const imagingTypes = new Set(["xray", "ecg", "ct", "mri"])

export default function DashboardPage() {
    const { role, user } = useAuth()

    if (role === "patient") {
        return <PatientDashboard userId={user?.id ?? ""} />
    }

    return <DoctorDashboard doctorId={user?.id} />
}

function DoctorDashboard({ doctorId }: { doctorId?: string }) {
    const [search, setSearch] = useState("")
    const [selectedPatientIdState, setSelectedPatientIdState] = useState("")
    const debouncedSearch = useDebounce(search, 300)

    const {
        data: patientsData,
        isLoading: isPatientsLoading,
        error: patientsError,
    } = usePatients({
        page: 1,
        pageSize: 50,
        search: debouncedSearch || undefined,
    })
    const { data: statsData } = useDashboardStats(doctorId)
    const patients = useMemo(() => patientsData?.patients ?? [], [patientsData?.patients])
    const selectedPatientId = useMemo(() => {
        if (patients.length === 0) return ""
        const selectedStillVisible = patients.some((patient) => patient.id === selectedPatientIdState)
        if (selectedPatientIdState && selectedStillVisible) return selectedPatientIdState
        return patients[0].id
    }, [patients, selectedPatientIdState])

    const selectedPatient = useMemo(
        () => patients.find((patient) => patient.id === selectedPatientId),
        [patients, selectedPatientId]
    )

    const { data: selectedPatientDetail } = usePatient(selectedPatientId)
    const { data: selectedPatientRecords, isLoading: isRecordsLoading } = usePatientRecords(
        selectedPatientId,
        undefined,
        50
    )
    const records = selectedPatientRecords?.records ?? []
    const latestRecord = records[0]
    const imagingCount = records.filter((record) => imagingTypes.has(record.record_type)).length
    const labCount = records.filter((record) => record.record_type === "lab").length

    return (
        <div className="space-y-6">
            <header className="space-y-1">
                <h1 className="text-2xl font-bold text-[#1e2939]">Dashboard bác sĩ</h1>
                <p className="text-sm text-[#4a5565]">
                    Dữ liệu đang được tải trực tiếp từ API bệnh nhân và hồ sơ y khoa.
                </p>
            </header>

            <div className="grid gap-4 md:grid-cols-5">
                <StatCard label="Tổng bệnh nhân" value={statsData?.total_patients} />
                <StatCard label="Ca khẩn cấp" value={statsData?.urgent_cases} />
                <StatCard label="Ưu tiên cao" value={statsData?.high_priority} />
                <StatCard label="Đang chờ tư vấn" value={statsData?.pending_consultations} />
                <StatCard label="Cảnh báo" value={statsData?.alerts} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
                <Card className="bg-white/70">
                    <CardHeader>
                        <CardTitle>Danh sách bệnh nhân</CardTitle>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                placeholder="Tìm theo tên hoặc số điện thoại"
                                className="pl-9 bg-white/90"
                            />
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-3 max-h-[72vh] overflow-y-auto">
                        {isPatientsLoading && (
                            <p className="text-sm text-muted-foreground">Đang tải danh sách bệnh nhân...</p>
                        )}
                        {patientsError && (
                            <p className="text-sm text-destructive">
                                Không thể tải danh sách bệnh nhân. Vui lòng kiểm tra API backend.
                            </p>
                        )}
                        {!isPatientsLoading && !patientsError && patients.length === 0 && (
                            <p className="text-sm text-muted-foreground">Không có bệnh nhân phù hợp.</p>
                        )}

                        {patients.map((patient) => {
                            const age = calculateAge(patient.date_of_birth)
                            const isSelected = patient.id === selectedPatientId
                            return (
                                <button
                                    key={patient.id}
                                    type="button"
                                    onClick={() => setSelectedPatientIdState(patient.id)}
                                    className={`w-full rounded-xl border p-3 text-left transition ${
                                        isSelected
                                            ? "border-primary bg-primary/5"
                                            : "border-border hover:border-primary/40 hover:bg-white/60"
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <p className="font-semibold text-foreground">{patient.full_name}</p>
                                        {patient.triage_priority && (
                                            <Badge variant="outline">{priorityLabel(patient.triage_priority)}</Badge>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {age} tuổi • {patient.gender === "male" ? "Nam" : patient.gender === "female" ? "Nữ" : "Khác"}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Khám gần nhất: {formatDate(patient.last_checkup_date)}
                                    </p>
                                </button>
                            )
                        })}
                    </CardContent>
                </Card>

                <Card className="bg-white/70">
                    <CardContent className="p-6 space-y-5">
                        {!selectedPatient && (
                            <p className="text-sm text-muted-foreground">
                                Chọn bệnh nhân để xem chi tiết.
                            </p>
                        )}

                        {selectedPatient && (
                            <>
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex items-start gap-3">
                                        <div className="h-12 w-12 rounded-xl bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] text-white flex items-center justify-center">
                                            <User className="h-6 w-6" />
                                        </div>
                                        <div>
                                            <h2 className="text-xl font-bold text-foreground">{selectedPatient.full_name}</h2>
                                            <p className="text-sm text-muted-foreground">
                                                {calculateAge(selectedPatient.date_of_birth)} tuổi •{" "}
                                                {selectedPatient.gender === "male" ? "Nam" : selectedPatient.gender === "female" ? "Nữ" : "Khác"}
                                            </p>
                                            {selectedPatient.triage_priority && (
                                                <p className="text-sm text-orange-600 font-semibold mt-1">
                                                    {priorityLabel(selectedPatient.triage_priority)}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                    <div className="text-right text-sm">
                                        <p className="text-muted-foreground">
                                            Khám gần nhất: {formatDate(selectedPatient.last_checkup_date)}
                                        </p>
                                        <p className="font-semibold text-[#4A9FD8]">
                                            Tái khám: {formatDate(selectedPatient.next_appointment_date)}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    {(selectedPatient.chronic_conditions ?? []).map((condition) => (
                                        <Badge key={`${selectedPatient.id}-${condition.icd10_code}`} variant="secondary">
                                            {condition.name}
                                        </Badge>
                                    ))}
                                    {(selectedPatient.chronic_conditions ?? []).length === 0 && (
                                        <p className="text-sm text-muted-foreground">Chưa có bệnh mạn tính được khai báo.</p>
                                    )}
                                </div>

                                <div className="rounded-xl border bg-white/80 p-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <p className="font-semibold">Khám gần nhất</p>
                                        <Badge variant="outline">
                                            {latestRecord ? formatDateTime(latestRecord.created_at) : "Chưa có"}
                                        </Badge>
                                    </div>
                                    {isRecordsLoading && (
                                        <p className="text-sm text-muted-foreground mt-2">Đang tải hồ sơ y khoa...</p>
                                    )}
                                    {!isRecordsLoading && latestRecord && (
                                        <div className="mt-2 space-y-1">
                                            <p className="font-medium text-sm">{latestRecord.title}</p>
                                            <p className="text-sm text-muted-foreground">
                                                {latestRecord.content_text?.slice(0, 220) || "Không có tóm tắt nội dung."}
                                            </p>
                                        </div>
                                    )}
                                    {!isRecordsLoading && !latestRecord && (
                                        <p className="text-sm text-muted-foreground mt-2">Bệnh nhân chưa có hồ sơ y khoa.</p>
                                    )}
                                </div>

                                <div className="grid gap-3 md:grid-cols-3">
                                    <MiniStat icon={<FileText className="h-4 w-4" />} label="Tổng hồ sơ" value={records.length} />
                                    <MiniStat icon={<Activity className="h-4 w-4" />} label="Xét nghiệm" value={labCount} />
                                    <MiniStat icon={<ImageIcon className="h-4 w-4" />} label="Hình ảnh" value={imagingCount} />
                                </div>

                                <div className="flex justify-end">
                                    <Button asChild>
                                        <Link href={`/dashboard/patients/${selectedPatient.id}`}>
                                            Mở hồ sơ đầy đủ <ArrowRight className="h-4 w-4" />
                                        </Link>
                                    </Button>
                                </div>

                                {selectedPatientDetail?.recent_vitals && selectedPatientDetail.recent_vitals.length > 0 && (
                                    <div className="rounded-xl border bg-white/80 p-4">
                                        <p className="font-semibold mb-2">Sinh hiệu gần đây</p>
                                        <div className="flex flex-wrap gap-2">
                                            {formatVitalSummary(selectedPatientDetail.recent_vitals[0]).map((item) => (
                                                <Badge key={item} variant="outline">{item}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}

function PatientDashboard({ userId }: { userId: string }) {
    const { data: patientData, isLoading: patientLoading } = usePatient(userId)
    const { data: recordsData, isLoading: recordsLoading } = usePatientRecords(userId, undefined, 20)
    const records = recordsData?.records ?? []
    const latestRecord = records[0]

    return (
        <div className="space-y-6">
            <header className="space-y-1">
                <h1 className="text-2xl font-bold text-[#1e2939]">Dashboard bệnh nhân</h1>
                <p className="text-sm text-[#4a5565]">
                    Hồ sơ cá nhân đang được đồng bộ trực tiếp từ cơ sở dữ liệu.
                </p>
            </header>

            <Card className="bg-white/70">
                <CardContent className="p-6 space-y-4">
                    {patientLoading && <p className="text-sm text-muted-foreground">Đang tải hồ sơ cá nhân...</p>}
                    {!patientLoading && !patientData?.patient && (
                        <p className="text-sm text-muted-foreground">
                            Chưa tìm thấy dữ liệu bệnh nhân cho tài khoản này.
                        </p>
                    )}
                    {patientData?.patient && (
                        <>
                            <div>
                                <h2 className="text-xl font-bold">{patientData.patient.full_name}</h2>
                                <p className="text-sm text-muted-foreground">
                                    Khám gần nhất: {formatDate(patientData.patient.last_checkup_date)}
                                </p>
                            </div>
                            <div className="grid gap-3 md:grid-cols-3">
                                <MiniStat icon={<FileText className="h-4 w-4" />} label="Tổng hồ sơ" value={records.length} />
                                <MiniStat
                                    icon={<Activity className="h-4 w-4" />}
                                    label="Sinh hiệu"
                                    value={patientData.recent_vitals.length}
                                />
                                <MiniStat
                                    icon={<ImageIcon className="h-4 w-4" />}
                                    label="Hồ sơ mới nhất"
                                    value={latestRecord ? formatDateTime(latestRecord.created_at) : "Chưa có"}
                                />
                            </div>
                            <div className="flex justify-end">
                                <Button asChild>
                                    <Link href="/dashboard/records">
                                        Xem toàn bộ hồ sơ <ArrowRight className="h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </>
                    )}
                    {recordsLoading && (
                        <p className="text-xs text-muted-foreground">Đang tải lịch sử hồ sơ...</p>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}

function StatCard({ label, value }: { label: string; value?: number }) {
    return (
        <Card className="bg-white/70">
            <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-1 text-2xl font-bold">{value ?? 0}</p>
            </CardContent>
        </Card>
    )
}

function MiniStat({
    icon,
    label,
    value,
}: {
    icon: ReactNode
    label: string
    value: string | number
}) {
    return (
        <div className="rounded-xl border bg-white p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {icon}
                <span>{label}</span>
            </div>
            <p className="mt-1 text-xl font-bold">{value}</p>
        </div>
    )
}

function calculateAge(dateOfBirth: string): number {
    const birthDate = new Date(dateOfBirth)
    if (Number.isNaN(birthDate.getTime())) return 0

    const today = new Date()
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age -= 1
    }
    return age
}

function formatDate(value?: string): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString("vi-VN")
}

function formatDateTime(value?: string): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    })
}

function priorityLabel(priority: "low" | "medium" | "high" | "urgent"): string {
    switch (priority) {
        case "urgent":
            return "Khẩn cấp"
        case "high":
            return "Ưu tiên cao"
        case "medium":
            return "Trung bình"
        default:
            return "Thấp"
    }
}

function formatVitalSummary(vital: {
    blood_pressure_systolic?: number
    blood_pressure_diastolic?: number
    heart_rate?: number
    blood_glucose?: number
    oxygen_saturation?: number
}): string[] {
    const output: string[] = []
    if (vital.blood_pressure_systolic || vital.blood_pressure_diastolic) {
        output.push(`HA ${vital.blood_pressure_systolic ?? "--"}/${vital.blood_pressure_diastolic ?? "--"} mmHg`)
    }
    if (vital.heart_rate) output.push(`Mạch ${vital.heart_rate} bpm`)
    if (vital.blood_glucose) output.push(`Đường huyết ${vital.blood_glucose} mmol/L`)
    if (vital.oxygen_saturation) output.push(`SpO₂ ${vital.oxygen_saturation}%`)
    return output
}
