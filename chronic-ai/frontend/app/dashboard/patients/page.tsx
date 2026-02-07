/**
 * Patient list page with search, filter, and pagination
 */
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { usePatients } from "@/lib/hooks"
import { useDebounce } from "@/lib/hooks"
import { PageHeader, LoadingOverlay } from "@/components/shared"
import { PatientCard } from "@/components/medical/patient-card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, Filter, ChevronLeft, ChevronRight, Users } from "lucide-react"

export default function PatientsPage() {
    const router = useRouter()

    const [search, setSearch] = useState("")
    const [priority, setPriority] = useState("")
    const [page, setPage] = useState(1)

    const debouncedSearch = useDebounce(search, 300)

    const { data, isLoading, error } = usePatients({
        page,
        pageSize: 12,
        search: debouncedSearch || undefined,
        priority: priority || undefined,
    })

    const handlePatientClick = (patientId: string) => {
        router.push(`/dashboard/patients/${patientId}`)
    }

    const priorityOptions = [
        { value: "", label: "Tất cả" },
        { value: "urgent", label: "Khẩn cấp" },
        { value: "high", label: "Ưu tiên cao" },
        { value: "medium", label: "Trung bình" },
        { value: "low", label: "Thấp" },
    ]

    return (
        <div className="space-y-6">
            <PageHeader
                title="Danh sách bệnh nhân"
                description={`Tổng cộng ${data?.total || 0} bệnh nhân đang quản lý`}
            />

            {/* Search and Filter */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Tìm kiếm theo tên bệnh nhân..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value)
                            setPage(1)
                        }}
                        className="pl-9"
                    />
                </div>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" className="flex items-center gap-2">
                            <Filter className="h-4 w-4" />
                            <span className="hidden sm:inline">
                                {priorityOptions.find(p => p.value === priority)?.label || "Lọc"}
                            </span>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        {priorityOptions.map((option) => (
                            <DropdownMenuItem
                                key={option.value}
                                onClick={() => {
                                    setPriority(option.value)
                                    setPage(1)
                                }}
                            >
                                {option.label}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            {/* Loading State */}
            {isLoading && (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-4">
                                <div className="flex gap-3">
                                    <Skeleton className="h-12 w-12 rounded-full" />
                                    <div className="space-y-2 flex-1">
                                        <Skeleton className="h-4 w-3/4" />
                                        <Skeleton className="h-3 w-1/2" />
                                    </div>
                                </div>
                                <div className="mt-4 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-4 w-2/3" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Error State */}
            {error && (
                <Card className="border-destructive/30 bg-destructive/5">
                    <CardContent className="p-6 text-center">
                        <p className="text-destructive font-medium">Lỗi tải dữ liệu</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            Vui lòng kiểm tra kết nối và thử lại
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Patient Grid */}
            {!isLoading && data && (
                <>
                    {data.patients.length > 0 ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {data.patients.map((patient) => (
                                <PatientCard
                                    key={patient.id}
                                    patient={patient}
                                    onClick={() => handlePatientClick(patient.id)}
                                />
                            ))}
                        </div>
                    ) : (
                        <Card>
                            <CardContent className="p-12 text-center">
                                <Users className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                                <h3 className="font-medium text-foreground">Không tìm thấy bệnh nhân</h3>
                                <p className="text-sm text-muted-foreground mt-1">
                                    {search ? "Thử tìm kiếm với từ khóa khác" : "Chưa có bệnh nhân nào trong hệ thống"}
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Pagination */}
                    {data.total_pages > 1 && (
                        <div className="flex items-center justify-between">
                            <p className="text-sm text-muted-foreground">
                                Trang {page} / {data.total_pages}
                            </p>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page <= 1}
                                    onClick={() => setPage(page - 1)}
                                >
                                    <ChevronLeft className="h-4 w-4 mr-1" />
                                    Trước
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page >= data.total_pages}
                                    onClick={() => setPage(page + 1)}
                                >
                                    Sau
                                    <ChevronRight className="h-4 w-4 ml-1" />
                                </Button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
