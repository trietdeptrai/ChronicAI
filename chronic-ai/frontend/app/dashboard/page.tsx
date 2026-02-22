"use client"

import Link from "next/link"
import { useMemo, useState, type ReactNode } from "react"
import { useAuth, useDashboardLanguage, type DashboardLanguage } from "@/contexts"
import { useDebounce, useDashboardStats, usePatient, usePatientRecords, usePatients } from "@/lib/hooks"
import { Button } from "@/components/button"
import { Input } from "@/components/input"
import { Badge } from "@/components/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/card"
import { User, Search, FileText, Activity, Image as ImageIcon, ArrowRight } from "lucide-react"

const imagingTypes = new Set(["xray", "ecg", "ct", "mri"])

const dashboardCopy = {
    vi: {
        doctorTitle: "Bảng điều khiển bác sĩ",
        doctorDescription: "Theo dõi bệnh nhân và hồ sơ y khoa theo thời gian thực.",
        statTotalPatients: "Tổng bệnh nhân",
        statUrgentCases: "Ca khẩn cấp",
        statHighPriority: "Ưu tiên cao",
        statPendingConsultations: "Đang chờ tư vấn",
        statAlerts: "Cảnh báo",
        patientsListTitle: "Danh sách bệnh nhân",
        patientsSearchPlaceholder: "Tìm theo tên hoặc số điện thoại",
        loadingPatients: "Đang tải danh sách bệnh nhân...",
        patientsLoadError: "Không thể tải danh sách bệnh nhân. Vui lòng kiểm tra backend.",
        noPatients: "Không có bệnh nhân phù hợp.",
        yearsOld: "tuổi",
        lastCheckup: "Khám gần nhất",
        selectPatientPrompt: "Chọn bệnh nhân để xem chi tiết.",
        nextAppointment: "Tái khám",
        noChronicConditions: "Chưa có bệnh mạn tính được khai báo.",
        latestRecordTitle: "Hồ sơ gần nhất",
        noRecordYet: "Chưa có",
        loadingRecords: "Đang tải hồ sơ y khoa...",
        noRecordSummary: "Không có tóm tắt nội dung.",
        noMedicalRecords: "Bệnh nhân chưa có hồ sơ y khoa.",
        statTotalRecords: "Tổng hồ sơ",
        statLabs: "Xét nghiệm",
        statImaging: "Hình ảnh",
        openPatientProfile: "Mở hồ sơ đầy đủ",
        latestVitalsTitle: "Sinh hiệu gần đây",
        patientTitle: "Bảng điều khiển bệnh nhân",
        patientDescription: "Theo dõi hồ sơ cá nhân và chỉ số sức khỏe của bạn.",
        loadingProfile: "Đang tải hồ sơ cá nhân...",
        noProfile: "Chưa tìm thấy dữ liệu bệnh nhân cho tài khoản này.",
        statVitals: "Sinh hiệu",
        statNewestRecord: "Hồ sơ mới nhất",
        loadingHistory: "Đang tải lịch sử hồ sơ...",
        gender: {
            male: "Nam",
            female: "Nữ",
            other: "Khác",
        },
        priority: {
            urgent: "Khẩn cấp",
            high: "Ưu tiên cao",
            medium: "Trung bình",
            low: "Thấp",
        },
        vitals: {
            bloodPressure: "HA",
            heartRate: "Mạch",
            bloodGlucose: "Đường huyết",
            oxygenSaturation: "SpO2",
        },
    },
    en: {
        doctorTitle: "Doctor Dashboard",
        doctorDescription: "Monitor patients and medical records in real time.",
        statTotalPatients: "Total Patients",
        statUrgentCases: "Urgent Cases",
        statHighPriority: "High Priority",
        statPendingConsultations: "Pending Consults",
        statAlerts: "Alerts",
        patientsListTitle: "Patient List",
        patientsSearchPlaceholder: "Search by name or phone number",
        loadingPatients: "Loading patient list...",
        patientsLoadError: "Failed to load patients. Please check backend connectivity.",
        noPatients: "No matching patients.",
        yearsOld: "years old",
        lastCheckup: "Last checkup",
        selectPatientPrompt: "Select a patient to view details.",
        nextAppointment: "Next appointment",
        noChronicConditions: "No chronic conditions declared yet.",
        latestRecordTitle: "Latest Record",
        noRecordYet: "Not available",
        loadingRecords: "Loading medical records...",
        noRecordSummary: "No content summary available.",
        noMedicalRecords: "This patient has no medical records yet.",
        statTotalRecords: "Total Records",
        statLabs: "Labs",
        statImaging: "Imaging",
        openPatientProfile: "Open full profile",
        latestVitalsTitle: "Recent Vitals",
        patientTitle: "Patient Dashboard",
        patientDescription: "Track your profile and recent health indicators.",
        loadingProfile: "Loading your profile...",
        noProfile: "No patient data found for this account.",
        statVitals: "Vitals",
        statNewestRecord: "Latest Record",
        loadingHistory: "Loading record history...",
        gender: {
            male: "Male",
            female: "Female",
            other: "Other",
        },
        priority: {
            urgent: "Urgent",
            high: "High",
            medium: "Medium",
            low: "Low",
        },
        vitals: {
            bloodPressure: "BP",
            heartRate: "Heart rate",
            bloodGlucose: "Glucose",
            oxygenSaturation: "SpO2",
        },
    },
} as const

export default function DashboardPage() {
    const { role, user } = useAuth()
    const { language } = useDashboardLanguage()

    if (role === "patient") {
        return <PatientDashboard userId={user?.id ?? ""} language={language} />
    }

    return <DoctorDashboard doctorId={user?.id} language={language} />
}

function DoctorDashboard({ doctorId, language }: { doctorId?: string; language: DashboardLanguage }) {
    const t = dashboardCopy[language]
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
                <h1 className="text-2xl font-bold text-[#1e2939]">{t.doctorTitle}</h1>
                <p className="text-sm text-[#4a5565]">{t.doctorDescription}</p>
            </header>

            <div className="grid gap-4 md:grid-cols-5">
                <StatCard label={t.statTotalPatients} value={statsData?.total_patients} />
                <StatCard label={t.statUrgentCases} value={statsData?.urgent_cases} />
                <StatCard label={t.statHighPriority} value={statsData?.high_priority} />
                <StatCard label={t.statPendingConsultations} value={statsData?.pending_consultations} />
                <StatCard label={t.statAlerts} value={statsData?.alerts} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
                <Card className="bg-white/70">
                    <CardHeader>
                        <CardTitle>{t.patientsListTitle}</CardTitle>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                placeholder={t.patientsSearchPlaceholder}
                                className="pl-9 bg-white/90"
                            />
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-3 max-h-[72vh] overflow-y-auto">
                        {isPatientsLoading && (
                            <p className="text-sm text-muted-foreground">{t.loadingPatients}</p>
                        )}
                        {patientsError && (
                            <p className="text-sm text-destructive">{t.patientsLoadError}</p>
                        )}
                        {!isPatientsLoading && !patientsError && patients.length === 0 && (
                            <p className="text-sm text-muted-foreground">{t.noPatients}</p>
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
                                            <Badge variant="outline">{priorityLabel(patient.triage_priority, language)}</Badge>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {age} {t.yearsOld} - {genderLabel(patient.gender, language)}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {t.lastCheckup}: {formatDate(patient.last_checkup_date, language)}
                                    </p>
                                </button>
                            )
                        })}
                    </CardContent>
                </Card>

                <Card className="bg-white/70">
                    <CardContent className="p-6 space-y-5">
                        {!selectedPatient && (
                            <p className="text-sm text-muted-foreground">{t.selectPatientPrompt}</p>
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
                                                {calculateAge(selectedPatient.date_of_birth)} {t.yearsOld} -{" "}
                                                {genderLabel(selectedPatient.gender, language)}
                                            </p>
                                            {selectedPatient.triage_priority && (
                                                <p className="text-sm text-orange-600 font-semibold mt-1">
                                                    {priorityLabel(selectedPatient.triage_priority, language)}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                    <div className="text-right text-sm">
                                        <p className="text-muted-foreground">
                                            {t.lastCheckup}: {formatDate(selectedPatient.last_checkup_date, language)}
                                        </p>
                                        <p className="font-semibold text-[#4A9FD8]">
                                            {t.nextAppointment}: {formatDate(selectedPatient.next_appointment_date, language)}
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
                                        <p className="text-sm text-muted-foreground">{t.noChronicConditions}</p>
                                    )}
                                </div>

                                <div className="rounded-xl border bg-white/80 p-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <p className="font-semibold">{t.latestRecordTitle}</p>
                                        <Badge variant="outline">
                                            {latestRecord ? formatDateTime(latestRecord.created_at, language) : t.noRecordYet}
                                        </Badge>
                                    </div>
                                    {isRecordsLoading && (
                                        <p className="text-sm text-muted-foreground mt-2">{t.loadingRecords}</p>
                                    )}
                                    {!isRecordsLoading && latestRecord && (
                                        <div className="mt-2 space-y-1">
                                            <p className="font-medium text-sm">{latestRecord.title}</p>
                                            <p className="text-sm text-muted-foreground">
                                                {latestRecord.content_text?.slice(0, 220) || t.noRecordSummary}
                                            </p>
                                        </div>
                                    )}
                                    {!isRecordsLoading && !latestRecord && (
                                        <p className="text-sm text-muted-foreground mt-2">{t.noMedicalRecords}</p>
                                    )}
                                </div>

                                <div className="grid gap-3 md:grid-cols-3">
                                    <MiniStat icon={<FileText className="h-4 w-4" />} label={t.statTotalRecords} value={records.length} />
                                    <MiniStat icon={<Activity className="h-4 w-4" />} label={t.statLabs} value={labCount} />
                                    <MiniStat icon={<ImageIcon className="h-4 w-4" />} label={t.statImaging} value={imagingCount} />
                                </div>

                                <div className="flex justify-end">
                                    <Button asChild>
                                        <Link href={`/dashboard/patients/${selectedPatient.id}`}>
                                            {t.openPatientProfile} <ArrowRight className="h-4 w-4" />
                                        </Link>
                                    </Button>
                                </div>

                                {selectedPatientDetail?.recent_vitals && selectedPatientDetail.recent_vitals.length > 0 && (
                                    <div className="rounded-xl border bg-white/80 p-4">
                                        <p className="font-semibold mb-2">{t.latestVitalsTitle}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {formatVitalSummary(selectedPatientDetail.recent_vitals[0], language).map((item) => (
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

function PatientDashboard({ userId, language }: { userId: string; language: DashboardLanguage }) {
    const t = dashboardCopy[language]
    const { data: patientData, isLoading: patientLoading } = usePatient(userId)
    const { data: recordsData, isLoading: recordsLoading } = usePatientRecords(userId, undefined, 20)
    const records = recordsData?.records ?? []
    const latestRecord = records[0]

    return (
        <div className="space-y-6">
            <header className="space-y-1">
                <h1 className="text-2xl font-bold text-[#1e2939]">{t.patientTitle}</h1>
                <p className="text-sm text-[#4a5565]">{t.patientDescription}</p>
            </header>

            <Card className="bg-white/70">
                <CardContent className="p-6 space-y-4">
                    {patientLoading && <p className="text-sm text-muted-foreground">{t.loadingProfile}</p>}
                    {!patientLoading && !patientData?.patient && (
                        <p className="text-sm text-muted-foreground">{t.noProfile}</p>
                    )}
                    {patientData?.patient && (
                        <>
                            <div>
                                <h2 className="text-xl font-bold">{patientData.patient.full_name}</h2>
                                <p className="text-sm text-muted-foreground">
                                    {t.lastCheckup}: {formatDate(patientData.patient.last_checkup_date, language)}
                                </p>
                            </div>
                            <div className="grid gap-3 md:grid-cols-3">
                                <MiniStat icon={<FileText className="h-4 w-4" />} label={t.statTotalRecords} value={records.length} />
                                <MiniStat
                                    icon={<Activity className="h-4 w-4" />}
                                    label={t.statVitals}
                                    value={patientData.recent_vitals.length}
                                />
                                <MiniStat
                                    icon={<ImageIcon className="h-4 w-4" />}
                                    label={t.statNewestRecord}
                                    value={latestRecord ? formatDateTime(latestRecord.created_at, language) : t.noRecordYet}
                                />
                            </div>
                        </>
                    )}
                    {recordsLoading && (
                        <p className="text-xs text-muted-foreground">{t.loadingHistory}</p>
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

function formatDate(value: string | undefined, language: DashboardLanguage): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US")
}

function formatDateTime(value: string | undefined, language: DashboardLanguage): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString(language === "vi" ? "vi-VN" : "en-US", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    })
}

function priorityLabel(priority: "low" | "medium" | "high" | "urgent", language: DashboardLanguage): string {
    return dashboardCopy[language].priority[priority]
}

function genderLabel(gender: "male" | "female" | "other" | null | undefined, language: DashboardLanguage): string {
    if (!gender) return "--"
    return dashboardCopy[language].gender[gender]
}

function formatVitalSummary(vital: {
    blood_pressure_systolic?: number
    blood_pressure_diastolic?: number
    heart_rate?: number
    blood_glucose?: number
    oxygen_saturation?: number
}, language: DashboardLanguage): string[] {
    const output: string[] = []
    const labels = dashboardCopy[language].vitals
    if (vital.blood_pressure_systolic || vital.blood_pressure_diastolic) {
        output.push(`${labels.bloodPressure} ${vital.blood_pressure_systolic ?? "--"}/${vital.blood_pressure_diastolic ?? "--"} mmHg`)
    }
    if (vital.heart_rate) output.push(`${labels.heartRate} ${vital.heart_rate} bpm`)
    if (vital.blood_glucose) output.push(`${labels.bloodGlucose} ${vital.blood_glucose} mmol/L`)
    if (vital.oxygen_saturation) output.push(`${labels.oxygenSaturation} ${vital.oxygen_saturation}%`)
    return output
}
