/**
 * Patient records page
 */
"use client"

import { useState } from "react"
import Link from "next/link"
import { useAuth } from "@/contexts"
import { usePatientRecords } from "@/lib/hooks"
import { PageHeader, RecordAIAnalysis } from "@/components/shared"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import type { MedicalRecord } from "@/types"
import { FileText, ArrowRight } from "lucide-react"

const recordTypeOptions = [
    { value: "", label: "Tất cả" },
    { value: "prescription", label: "Đơn thuốc" },
    { value: "lab", label: "Xét nghiệm" },
    { value: "xray", label: "X-quang" },
    { value: "ecg", label: "ECG" },
    { value: "ct", label: "CT" },
    { value: "mri", label: "MRI" },
    { value: "notes", label: "Ghi chú" },
    { value: "referral", label: "Chuyển tuyến" },
]

const recordTypeLabels: Record<string, string> = {
    prescription: "Đơn thuốc",
    lab: "Xét nghiệm",
    xray: "X-quang",
    ecg: "ECG",
    ct: "CT",
    mri: "MRI",
    notes: "Ghi chú",
    referral: "Chuyển tuyến",
}

export default function RecordsPage() {
    const { role, user } = useAuth()
    const [recordFilter, setRecordFilter] = useState("")
    const [activeRecord, setActiveRecord] = useState<MedicalRecord | null>(null)

    const patientId = user?.id ?? ""
    const { data, isLoading, error } = usePatientRecords(
        patientId,
        recordFilter || undefined,
        50
    )

    if (role !== "patient") {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Hồ sơ y khoa"
                    description="Bác sĩ có thể xem hồ sơ trong trang chi tiết bệnh nhân"
                />
                <Card>
                    <CardContent className="p-8 text-center">
                        <FileText className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-sm text-muted-foreground mb-4">
                            Chọn một bệnh nhân để xem hồ sơ y khoa chi tiết.
                        </p>
                        <Button asChild variant="outline">
                            <Link href="/dashboard/patients">
                                Đi đến danh sách bệnh nhân <ArrowRight className="h-4 w-4 ml-1" />
                            </Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title="Hồ sơ y khoa"
                description="Theo dõi các tài liệu và kết quả đã lưu"
            />

            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <CardTitle>Tài liệu gần đây</CardTitle>
                        <p className="text-sm text-muted-foreground">
                            Lọc theo loại tài liệu để xem nhanh
                        </p>
                    </div>
                    <div className="w-full md:w-56">
                        <select
                            value={recordFilter}
                            onChange={(event) => setRecordFilter(event.target.value)}
                            className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                        >
                            {recordTypeOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {isLoading && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Đang tải hồ sơ y khoa...
                        </div>
                    )}

                    {error && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                            Không thể tải hồ sơ y khoa.
                        </div>
                    )}

                    {!isLoading && !error && data?.records.length === 0 && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Chưa có hồ sơ y khoa nào.
                        </div>
                    )}

                    {!isLoading && !error && data && data.records.length > 0 && (
                        <div className="space-y-3">
                            {data.records.map((record) => (
                                <div key={record.id} className="rounded-lg border p-4">
                                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <Badge variant="secondary">
                                                    {recordTypeLabels[record.record_type] ?? record.record_type}
                                                </Badge>
                                                {record.is_verified && (
                                                    <Badge variant="outline">Đã xác thực</Badge>
                                                )}
                                            </div>
                                            <p className="mt-2 text-sm font-semibold text-foreground">
                                                {record.title}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDateTime(record.created_at)}
                                            </p>
                                            {record.content_text && !hasAnalysis(record.analysis_result) && (
                                                <p className="mt-2 text-sm text-muted-foreground">
                                                    {truncateText(record.content_text, 180)}
                                                </p>
                                            )}
                                            <RecordAIAnalysis
                                                analysis={record.analysis_result}
                                                doctorComment={record.doctor_comment}
                                            />
                                        </div>
                                        <div className="flex flex-col gap-2 items-start md:items-end">
                                            {record.file_kind === "image" && record.file_url && (
                                                <button
                                                    type="button"
                                                    onClick={() => setActiveRecord(record)}
                                                    className="rounded-lg border overflow-hidden hover:ring-2 hover:ring-primary/30 transition"
                                                >
                                                    <img
                                                        src={record.file_url}
                                                        alt={record.title}
                                                        className="h-20 w-28 object-cover"
                                                    />
                                                </button>
                                            )}
                                            {record.file_kind === "pdf" && record.file_url && (
                                                <Button size="sm" variant="outline" asChild>
                                                    <a href={record.file_url} target="_blank" rel="noreferrer">
                                                        Tải PDF
                                                    </a>
                                                </Button>
                                            )}
                                            {!record.file_url && (
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <FileText className="h-4 w-4" />
                                                    <span>Không có tệp đính kèm</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog
                open={!!activeRecord}
                onOpenChange={(open) => {
                    if (!open) {
                        setActiveRecord(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>{activeRecord?.title || "Ảnh cận lâm sàng"}</DialogTitle>
                    </DialogHeader>
                    {activeRecord?.file_url ? (
                        <div className="space-y-3">
                            <img
                                src={activeRecord.file_url}
                                alt={activeRecord.title}
                                className="w-full rounded-lg border object-contain"
                            />
                            {activeRecord.content_text && !hasAnalysis(activeRecord.analysis_result) && (
                                <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground whitespace-pre-line">
                                    {activeRecord.content_text}
                                </div>
                            )}
                            <RecordAIAnalysis
                                analysis={activeRecord.analysis_result}
                                doctorComment={activeRecord.doctor_comment}
                            />
                        </div>
                    ) : (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Không có ảnh để hiển thị.
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    )
}

function formatDateTime(value: string): string {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
        return value
    }
    return date.toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    })
}

function truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text
    return `${text.slice(0, maxLength)}...`
}

function hasAnalysis(value: unknown): boolean {
    if (!value) return false
    if (typeof value === "string") return value.trim().length > 0
    if (typeof value === "object") return true
    return false
}
