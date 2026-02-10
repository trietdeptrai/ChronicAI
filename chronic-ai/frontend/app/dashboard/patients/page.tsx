/**
 * Doctor patient list page (live API data)
 */
"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts"
import { useDebounce, usePatients } from "@/lib/hooks"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Search, ArrowRight } from "lucide-react"

const priorityFilters = [
    { value: "", label: "Tất cả mức ưu tiên" },
    { value: "urgent", label: "Khẩn cấp" },
    { value: "high", label: "Ưu tiên cao" },
    { value: "medium", label: "Trung bình" },
    { value: "low", label: "Thấp" },
]

export default function PatientsPage() {
    const router = useRouter()
    const { role } = useAuth()
    const [search, setSearch] = useState("")
    const [priority, setPriority] = useState("")
    const debouncedSearch = useDebounce(search, 300)

    const { data, isLoading, error } = usePatients({
        page: 1,
        pageSize: 100,
        search: debouncedSearch || undefined,
        priority: priority || undefined,
    })

    const patients = data?.patients ?? []
    const pageLabel = useMemo(() => {
        if (!data) return ""
        return `Trang ${data.page}/${Math.max(data.total_pages, 1)} • ${data.total} bệnh nhân`
    }, [data])

    if (role !== "doctor") {
        return (
            <Card>
                <CardContent className="p-6 text-sm text-muted-foreground">
                    Danh sách bệnh nhân chỉ dành cho tài khoản bác sĩ.
                </CardContent>
            </Card>
        )
    }

    return (
        <div className="space-y-6">
            <div className="space-y-1">
                <h1 className="text-2xl font-bold text-[#1e2939]">Bệnh nhân</h1>
                <p className="text-sm text-[#4a5565]">
                    Danh sách này lấy trực tiếp từ endpoint `/doctor/patients`.
                </p>
            </div>

            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder="Tìm tên hoặc số điện thoại"
                            className="pl-9"
                        />
                    </div>
                    <div className="w-full md:w-64">
                        <select
                            value={priority}
                            onChange={(event) => setPriority(event.target.value)}
                            className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                        >
                            {priorityFilters.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3">
                    {pageLabel && <p className="text-xs text-muted-foreground">{pageLabel}</p>}

                    {isLoading && (
                        <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground text-center">
                            Đang tải danh sách bệnh nhân...
                        </div>
                    )}

                    {error && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                            Không thể tải dữ liệu bệnh nhân từ backend.
                        </div>
                    )}

                    {!isLoading && !error && patients.length === 0 && (
                        <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground text-center">
                            Không có bệnh nhân phù hợp.
                        </div>
                    )}

                    {!isLoading && !error && patients.length > 0 && (
                        <div className="grid gap-3 md:grid-cols-2">
                            {patients.map((patient) => (
                                <button
                                    key={patient.id}
                                    type="button"
                                    onClick={() => router.push(`/dashboard/patients/${patient.id}`)}
                                    className="w-full rounded-xl border bg-background p-4 text-left hover:border-primary/40 hover:shadow-sm transition"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="font-semibold text-foreground">{patient.full_name}</p>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                {formatGender(patient.gender)} • {patient.phone_primary}
                                            </p>
                                        </div>
                                        {patient.triage_priority && (
                                            <Badge variant="outline">
                                                {formatPriority(patient.triage_priority)}
                                            </Badge>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-2">
                                        Khám gần nhất: {formatDate(patient.last_checkup_date)}
                                    </p>
                                    <div className="mt-3 flex justify-end">
                                        <Button size="sm" variant="outline" asChild>
                                            <Link href={`/dashboard/patients/${patient.id}`}>
                                                Chi tiết <ArrowRight className="h-4 w-4 ml-1" />
                                            </Link>
                                        </Button>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}

function formatDate(value?: string): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString("vi-VN")
}

function formatGender(gender: "male" | "female" | "other"): string {
    switch (gender) {
        case "male":
            return "Nam"
        case "female":
            return "Nữ"
        default:
            return "Khác"
    }
}

function formatPriority(priority: "low" | "medium" | "high" | "urgent"): string {
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
