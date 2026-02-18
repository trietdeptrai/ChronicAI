/**
 * Doctor patient list page with patient profile CRUD.
 */
"use client"

import Link from "next/link"
import { useMemo, useRef, useState, type ChangeEvent, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ArrowRight, FileText, Search, Settings, Upload, UserPlus, X } from "lucide-react"

import { useAuth, useDashboardLanguage, type DashboardLanguage } from "@/contexts"
import {
    useCreatePatient,
    useDebounce,
    useDeletePatientProfile,
    useExportPatientMetadata,
    useImportPatientMetadataPreview,
    usePatients,
    useUpdatePatient,
} from "@/lib/hooks"
import type { Patient, PatientCreateInput, PatientUpdateInput } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/alert-dialog"

const priorityFilters = ["", "urgent", "high", "medium", "low"] as const
const genderOptions = ["female", "male", "other"] as const
const triageOptions = ["low", "medium", "high", "urgent"] as const
const statusOptions = ["active", "inactive", "deceased", "suspended"] as const

type PriorityFilter = (typeof priorityFilters)[number]
type KnownPriority = Exclude<PriorityFilter, "">
type GenderOption = (typeof genderOptions)[number]
type TriageOption = (typeof triageOptions)[number]
type StatusOption = (typeof statusOptions)[number]
type TextExportFormat = "json" | "pdf"

type Translation = {
    title: string
    description: string
    doctorOnly: string
    newPatient: string
    searchPlaceholder: string
    allPriorities: string
    pageLabel: (page: number, totalPages: number, total: number) => string
    loadingPatients: string
    loadPatientsError: string
    noMatchingPatients: string
    lastCheckup: string
    detail: string
    edit: string
    delete: string
    createPatient: string
    updatePatient: string
    cancel: string
    create: string
    creating: string
    save: string
    saving: string
    deleteDialogTitle: string
    deleteDialogDescription: string
    deleting: string
    requiredFieldsError: string
    createSuccess: string
    createFailure: string
    updateSuccess: string
    updateFailure: string
    deleteSuccess: string
    deleteFailure: string
    genderLabels: Record<GenderOption, string>
    priorityLabels: Record<KnownPriority, string>
    triageLabels: Record<TriageOption, string>
    statusLabels: Record<StatusOption, string>
    fieldLabels: {
        fullName: string
        dateOfBirth: string
        gender: string
        primaryPhone: string
        email: string
        ward: string
        district: string
        province: string
        emergencyContactName: string
        emergencyContactPhone: string
        emergencyRelationship: string
        triagePriority: string
        profileStatus: string
    }
}

const translations: Record<DashboardLanguage, Translation> = {
    vi: {
        title: "Bệnh nhân",
        description: "Quản lý thông tin hồ sơ bệnh nhân tách biệt với hồ sơ y khoa.",
        doctorOnly: "Trang này chỉ dành cho tài khoản bác sĩ.",
        newPatient: "Bệnh nhân mới",
        searchPlaceholder: "Tìm theo tên bệnh nhân",
        allPriorities: "Tất cả mức ưu tiên",
        pageLabel: (page, totalPages, total) =>
            `Trang ${page}/${Math.max(totalPages, 1)} - ${total} bệnh nhân`,
        loadingPatients: "Đang tải danh sách bệnh nhân...",
        loadPatientsError: "Không thể tải danh sách bệnh nhân.",
        noMatchingPatients: "Không có bệnh nhân phù hợp.",
        lastCheckup: "Lần khám gần nhất",
        detail: "Chi tiết",
        edit: "Chỉnh sửa",
        delete: "Xóa",
        createPatient: "Tạo bệnh nhân",
        updatePatient: "Cập nhật bệnh nhân",
        cancel: "Hủy",
        create: "Tạo",
        creating: "Đang tạo...",
        save: "Lưu",
        saving: "Đang lưu...",
        deleteDialogTitle: "Xóa hồ sơ bệnh nhân?",
        deleteDialogDescription: "Hành động này sẽ xóa thông tin hồ sơ bệnh nhân và bản ghi liên kết.",
        deleting: "Đang xóa...",
        requiredFieldsError: "Vui lòng điền đầy đủ các trường bắt buộc.",
        createSuccess: "Tạo bệnh nhân thành công.",
        createFailure: "Không thể tạo bệnh nhân.",
        updateSuccess: "Cập nhật bệnh nhân thành công.",
        updateFailure: "Không thể cập nhật bệnh nhân.",
        deleteSuccess: "Xóa bệnh nhân thành công.",
        deleteFailure: "Không thể xóa bệnh nhân.",
        genderLabels: {
            female: "Nữ",
            male: "Nam",
            other: "Khác",
        },
        priorityLabels: {
            urgent: "Khẩn cấp",
            high: "Cao",
            medium: "Trung bình",
            low: "Thấp",
        },
        triageLabels: {
            low: "Thấp",
            medium: "Trung bình",
            high: "Cao",
            urgent: "Khẩn cấp",
        },
        statusLabels: {
            active: "Đang hoạt động",
            inactive: "Tạm ngưng",
            deceased: "Đã mất",
            suspended: "Đình chỉ",
        },
        fieldLabels: {
            fullName: "Họ và tên *",
            dateOfBirth: "Ngày sinh *",
            gender: "Giới tính *",
            primaryPhone: "Số điện thoại *",
            email: "Email",
            ward: "Phường/Xã *",
            district: "Quận/Huyện *",
            province: "Tỉnh/Thành phố *",
            emergencyContactName: "Người liên hệ khẩn cấp *",
            emergencyContactPhone: "Số điện thoại khẩn cấp *",
            emergencyRelationship: "Mối quan hệ *",
            triagePriority: "Mức ưu tiên",
            profileStatus: "Trạng thái hồ sơ",
        },
    },
    en: {
        title: "Patients",
        description: "Manage patient profile information separately from medical files.",
        doctorOnly: "This page is available for doctor accounts only.",
        newPatient: "New Patient",
        searchPlaceholder: "Search by patient name",
        allPriorities: "All priorities",
        pageLabel: (page, totalPages, total) =>
            `Page ${page}/${Math.max(totalPages, 1)} - ${total} patients`,
        loadingPatients: "Loading patients...",
        loadPatientsError: "Failed to load patients.",
        noMatchingPatients: "No matching patients.",
        lastCheckup: "Last checkup",
        detail: "Detail",
        edit: "Edit",
        delete: "Delete",
        createPatient: "Create Patient",
        updatePatient: "Update Patient",
        cancel: "Cancel",
        create: "Create",
        creating: "Creating...",
        save: "Save",
        saving: "Saving...",
        deleteDialogTitle: "Delete patient profile?",
        deleteDialogDescription: "This action removes patient profile information and linked records.",
        deleting: "Deleting...",
        requiredFieldsError: "Please fill all required fields.",
        createSuccess: "Patient created successfully.",
        createFailure: "Failed to create patient.",
        updateSuccess: "Patient updated successfully.",
        updateFailure: "Failed to update patient.",
        deleteSuccess: "Patient deleted successfully.",
        deleteFailure: "Failed to delete patient.",
        genderLabels: {
            female: "Female",
            male: "Male",
            other: "Other",
        },
        priorityLabels: {
            urgent: "Urgent",
            high: "High",
            medium: "Medium",
            low: "Low",
        },
        triageLabels: {
            low: "Low",
            medium: "Medium",
            high: "High",
            urgent: "Urgent",
        },
        statusLabels: {
            active: "Active",
            inactive: "Inactive",
            deceased: "Deceased",
            suspended: "Suspended",
        },
        fieldLabels: {
            fullName: "Full Name *",
            dateOfBirth: "Date of Birth *",
            gender: "Gender *",
            primaryPhone: "Primary Phone *",
            email: "Email",
            ward: "Ward *",
            district: "District *",
            province: "Province *",
            emergencyContactName: "Emergency Contact Name *",
            emergencyContactPhone: "Emergency Contact Phone *",
            emergencyRelationship: "Emergency Relationship *",
            triagePriority: "Triage Priority",
            profileStatus: "Profile Status",
        },
    },
}

type PatientFormState = {
    full_name: string
    date_of_birth: string
    gender: "male" | "female" | "other"
    phone_primary: string
    email: string
    address_ward: string
    address_district: string
    address_province: string
    emergency_contact_name: string
    emergency_contact_phone: string
    emergency_contact_relationship: string
    triage_priority: "low" | "medium" | "high" | "urgent"
    profile_status: "active" | "inactive" | "deceased" | "suspended"
}

const EMPTY_FORM: PatientFormState = {
    full_name: "",
    date_of_birth: "",
    gender: "female",
    phone_primary: "",
    email: "",
    address_ward: "",
    address_district: "",
    address_province: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relationship: "",
    triage_priority: "low",
    profile_status: "active",
}

export default function PatientsPage() {
    const router = useRouter()
    const { role } = useAuth()
    const { language } = useDashboardLanguage()
    const [search, setSearch] = useState("")
    const [priority, setPriority] = useState("")
    const [createOpen, setCreateOpen] = useState(false)
    const [editPatient, setEditPatient] = useState<Patient | null>(null)
    const [deletePatient, setDeletePatient] = useState<Patient | null>(null)
    const [form, setForm] = useState<PatientFormState>(EMPTY_FORM)
    const [formError, setFormError] = useState<string | null>(null)
    const [metadataExportFormat, setMetadataExportFormat] = useState<TextExportFormat>("json")
    const metadataImportInputRef = useRef<HTMLInputElement>(null)
    const debouncedSearch = useDebounce(search, 300)
    const t = translations[language]
    const metadataActionText = language === "vi"
        ? {
            exportButton: "Xuất metadata",
            importButton: "Nhập metadata",
            exporting: "Đang xuất...",
            importing: "Đang nhập...",
            exportSuccess: "Đã xuất metadata bệnh nhân.",
            importSuccess: "Đã điền sẵn metadata từ tệp nhập. Vui lòng kiểm tra trước khi lưu.",
            exportFailed: "Xuất metadata thất bại.",
            importFailed: "Nhập metadata thất bại.",
            invalidFileType: "Tệp không hợp lệ. Chỉ hỗ trợ .json hoặc .pdf.",
            hint: "Nhập chỉ điền sẵn biểu mẫu, không tự lưu.",
            formatLabel: "Định dạng xuất metadata",
        }
        : {
            exportButton: "Export metadata",
            importButton: "Import metadata",
            exporting: "Exporting...",
            importing: "Importing...",
            exportSuccess: "Patient metadata exported.",
            importSuccess: "Form prefilled from imported metadata. Review before saving.",
            exportFailed: "Failed to export metadata.",
            importFailed: "Failed to import metadata.",
            invalidFileType: "Invalid file type. Only .json or .pdf is supported.",
            hint: "Import only prefills the form and does not save automatically.",
            formatLabel: "Metadata export format",
        }

    const listQuery = usePatients({
        page: 1,
        pageSize: 100,
        search: debouncedSearch || undefined,
        priority: priority || undefined,
    })
    const createMutation = useCreatePatient()
    const updateMutation = useUpdatePatient()
    const deleteMutation = useDeletePatientProfile()
    const exportMetadataMutation = useExportPatientMetadata()
    const importMetadataMutation = useImportPatientMetadataPreview()

    const patients = listQuery.data?.patients ?? []
    const pageLabel = useMemo(() => {
        if (!listQuery.data) return ""
        return t.pageLabel(listQuery.data.page, listQuery.data.total_pages, listQuery.data.total)
    }, [listQuery.data, t])

    if (role !== "doctor") {
        return (
            <Card>
                <CardContent className="p-6 text-sm text-muted-foreground">
                    {t.doctorOnly}
                </CardContent>
            </Card>
        )
    }

    const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending

    const openCreate = () => {
        setForm(EMPTY_FORM)
        setFormError(null)
        setCreateOpen(true)
    }

    const openEdit = (patient: Patient) => {
        setForm({
            full_name: patient.full_name ?? "",
            date_of_birth: patient.date_of_birth ?? "",
            gender: patient.gender ?? "female",
            phone_primary: patient.phone_primary ?? "",
            email: patient.email ?? "",
            address_ward: patient.address_ward ?? "",
            address_district: patient.address_district ?? "",
            address_province: patient.address_province ?? "",
            emergency_contact_name: patient.emergency_contact_name ?? "",
            emergency_contact_phone: patient.emergency_contact_phone ?? "",
            emergency_contact_relationship: patient.emergency_contact_relationship ?? "",
            triage_priority: patient.triage_priority ?? "low",
            profile_status: patient.profile_status ?? "active",
        })
        setFormError(null)
        setEditPatient(patient)
    }

    const validateForm = (): string | null => {
        const required = [
            form.full_name,
            form.date_of_birth,
            form.phone_primary,
            form.address_ward,
            form.address_district,
            form.address_province,
            form.emergency_contact_name,
            form.emergency_contact_phone,
            form.emergency_contact_relationship,
        ]
        return required.some((value) => !value.trim()) ? t.requiredFieldsError : null
    }

    const buildCreatePayload = (): PatientCreateInput => ({
        full_name: form.full_name.trim(),
        date_of_birth: form.date_of_birth,
        gender: form.gender,
        phone_primary: form.phone_primary.trim(),
        email: normalizeOptional(form.email) || undefined,
        address_ward: form.address_ward.trim(),
        address_district: form.address_district.trim(),
        address_province: form.address_province.trim(),
        emergency_contact_name: form.emergency_contact_name.trim(),
        emergency_contact_phone: form.emergency_contact_phone.trim(),
        emergency_contact_relationship: form.emergency_contact_relationship.trim(),
        triage_priority: form.triage_priority,
        profile_status: form.profile_status,
    })

    const buildUpdatePayload = (): PatientUpdateInput => ({
        full_name: form.full_name.trim(),
        date_of_birth: form.date_of_birth,
        gender: form.gender,
        phone_primary: form.phone_primary.trim(),
        email: normalizeOptional(form.email),
        address_ward: form.address_ward.trim(),
        address_district: form.address_district.trim(),
        address_province: form.address_province.trim(),
        emergency_contact_name: form.emergency_contact_name.trim(),
        emergency_contact_phone: form.emergency_contact_phone.trim(),
        emergency_contact_relationship: form.emergency_contact_relationship.trim(),
        triage_priority: form.triage_priority,
        profile_status: form.profile_status,
    })

    const submitCreate = () => {
        const err = validateForm()
        if (err) {
            setFormError(err)
            return
        }
        createMutation.mutate(buildCreatePayload(), {
            onSuccess: () => {
                setCreateOpen(false)
                setForm(EMPTY_FORM)
                setFormError(null)
                toast.success(t.createSuccess)
            },
            onError: (error) => setFormError(getErrorMessage(error, t.createFailure)),
        })
    }

    const submitUpdate = () => {
        if (!editPatient) return
        const err = validateForm()
        if (err) {
            setFormError(err)
            return
        }
        updateMutation.mutate(
            { patientId: editPatient.id, data: buildUpdatePayload() },
            {
                onSuccess: () => {
                    setEditPatient(null)
                    setForm(EMPTY_FORM)
                    setFormError(null)
                    toast.success(t.updateSuccess)
                },
                onError: (error) => setFormError(getErrorMessage(error, t.updateFailure)),
            }
        )
    }

    const submitDelete = () => {
        if (!deletePatient) return
        deleteMutation.mutate(
            { patientId: deletePatient.id },
            {
                onSuccess: (result) => {
                    toast.success(result.warning ? `${t.deleteSuccess} ${result.warning}` : t.deleteSuccess)
                    setDeletePatient(null)
                },
                onError: (error) => toast.error(getErrorMessage(error, t.deleteFailure)),
            }
        )
    }

    const buildMetadataPayloadFromForm = () => {
        const payload = {
            full_name: form.full_name.trim() || undefined,
            date_of_birth: form.date_of_birth || undefined,
            gender: form.gender || undefined,
            phone_primary: form.phone_primary.trim() || undefined,
            email: form.email.trim() || undefined,
            address_ward: form.address_ward.trim() || undefined,
            address_district: form.address_district.trim() || undefined,
            address_province: form.address_province.trim() || undefined,
            emergency_contact_name: form.emergency_contact_name.trim() || undefined,
            emergency_contact_phone: form.emergency_contact_phone.trim() || undefined,
            emergency_contact_relationship: form.emergency_contact_relationship.trim() || undefined,
            triage_priority: form.triage_priority || undefined,
            profile_status: form.profile_status || undefined,
        }
        return payload
    }

    const applyImportedMetadataToForm = (metadata: Record<string, unknown>) => {
        setForm((prev) => ({
            ...prev,
            full_name: typeof metadata.full_name === "string" ? metadata.full_name : prev.full_name,
            date_of_birth: typeof metadata.date_of_birth === "string" ? metadata.date_of_birth : prev.date_of_birth,
            gender: metadata.gender === "male" || metadata.gender === "female" || metadata.gender === "other"
                ? metadata.gender
                : prev.gender,
            phone_primary: typeof metadata.phone_primary === "string" ? metadata.phone_primary : prev.phone_primary,
            email: typeof metadata.email === "string" ? metadata.email : prev.email,
            address_ward: typeof metadata.address_ward === "string" ? metadata.address_ward : prev.address_ward,
            address_district: typeof metadata.address_district === "string" ? metadata.address_district : prev.address_district,
            address_province: typeof metadata.address_province === "string" ? metadata.address_province : prev.address_province,
            emergency_contact_name: typeof metadata.emergency_contact_name === "string" ? metadata.emergency_contact_name : prev.emergency_contact_name,
            emergency_contact_phone: typeof metadata.emergency_contact_phone === "string" ? metadata.emergency_contact_phone : prev.emergency_contact_phone,
            emergency_contact_relationship: typeof metadata.emergency_contact_relationship === "string"
                ? metadata.emergency_contact_relationship
                : prev.emergency_contact_relationship,
            triage_priority: metadata.triage_priority === "low"
                || metadata.triage_priority === "medium"
                || metadata.triage_priority === "high"
                || metadata.triage_priority === "urgent"
                ? metadata.triage_priority
                : prev.triage_priority,
            profile_status: metadata.profile_status === "active"
                || metadata.profile_status === "inactive"
                || metadata.profile_status === "deceased"
                || metadata.profile_status === "suspended"
                ? metadata.profile_status
                : prev.profile_status,
        }))
    }

    const handleMetadataExport = () => {
        exportMetadataMutation.mutate(
            {
                metadata: buildMetadataPayloadFromForm(),
                format: metadataExportFormat,
                language,
            },
            {
                onSuccess: (result) => {
                    const fallbackName = buildDownloadName(
                        form.full_name,
                        `patient-metadata.${metadataExportFormat}`,
                        "-metadata"
                    )
                    triggerFileDownload(result.blob, result.filename ?? fallbackName)
                    toast.success(metadataActionText.exportSuccess)
                },
                onError: (error) => {
                    toast.error(getErrorMessage(error, metadataActionText.exportFailed))
                },
            }
        )
    }

    const handleMetadataImportButtonClick = () => {
        metadataImportInputRef.current?.click()
    }

    const handleMetadataImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        if (!selected) return

        const resetInput = () => {
            if (metadataImportInputRef.current) {
                metadataImportInputRef.current.value = ""
            }
        }

        const lowerName = selected.name.toLowerCase()
        if (!lowerName.endsWith(".json") && !lowerName.endsWith(".pdf")) {
            toast.error(metadataActionText.invalidFileType)
            resetInput()
            return
        }

        importMetadataMutation.mutate(
            { file: selected },
            {
                onSuccess: (result) => {
                    applyImportedMetadataToForm(result.metadata as Record<string, unknown>)
                    toast.success(metadataActionText.importSuccess)
                },
                onError: (error) => {
                    toast.error(getErrorMessage(error, metadataActionText.importFailed))
                },
                onSettled: () => {
                    resetInput()
                },
            }
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div className="space-y-1">
                    <h1 className="text-2xl font-bold text-[#1e2939]">{t.title}</h1>
                    <p className="text-sm text-[#4a5565]">{t.description}</p>
                </div>
                <Button onClick={openCreate}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    {t.newPatient}
                </Button>
            </div>

            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t.searchPlaceholder} className="pl-9" />
                    </div>
                    <div className="w-full md:w-64">
                        <select value={priority} onChange={(e) => setPriority(e.target.value)} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs md:text-sm">
                            {priorityFilters.map((option) => (
                                <option key={option} value={option}>
                                    {option ? t.priorityLabels[option as KnownPriority] : t.allPriorities}
                                </option>
                            ))}
                        </select>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3">
                    {pageLabel && <p className="text-xs text-muted-foreground">{pageLabel}</p>}
                    {listQuery.isLoading && <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">{t.loadingPatients}</div>}
                    {listQuery.error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{t.loadPatientsError}</div>}
                    {!listQuery.isLoading && !listQuery.error && patients.length === 0 && <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">{t.noMatchingPatients}</div>}
                    {!listQuery.isLoading && !listQuery.error && patients.length > 0 && (
                        <div className="grid gap-3 md:grid-cols-2">
                            {patients.map((patient) => (
                                <div key={patient.id} className="rounded-xl border bg-background p-4 transition hover:border-primary/40 hover:shadow-sm">
                                    <button type="button" onClick={() => router.push(`/dashboard/patients/${patient.id}`)} className="w-full text-left">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="font-semibold text-foreground">{patient.full_name}</p>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    {getGenderLabel(patient.gender, t.genderLabels)} - {patient.phone_primary}
                                                </p>
                                            </div>
                                            {patient.triage_priority && (
                                                <Badge variant="outline">
                                                    {getPriorityLabel(patient.triage_priority, t.priorityLabels)}
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="mt-2 text-xs text-muted-foreground">{t.lastCheckup}: {formatDate(patient.last_checkup_date, language)}</p>
                                    </button>
                                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                                        <Button size="sm" variant="outline" asChild>
                                            <Link href={`/dashboard/patients/${patient.id}`}>{t.detail} <ArrowRight className="ml-1 h-4 w-4" /></Link>
                                        </Button>
                                        <Button size="sm" variant="outline" onClick={() => openEdit(patient)}><Settings className="mr-1 h-3.5 w-3.5" />{t.edit}</Button>
                                        <Button size="sm" variant="destructive" onClick={() => setDeletePatient(patient)}><X className="mr-1 h-3.5 w-3.5" />{t.delete}</Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <input
                ref={metadataImportInputRef}
                type="file"
                accept=".json,.pdf,application/json,application/pdf"
                className="hidden"
                onChange={handleMetadataImportFileChange}
            />

            <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) { setForm(EMPTY_FORM); setFormError(null) } }}>
                <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
                    <DialogHeader><DialogTitle>{t.createPatient}</DialogTitle></DialogHeader>
                    <div className="space-y-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                            <div className="flex w-full sm:w-auto">
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="rounded-r-none border-r-0"
                                    onClick={handleMetadataExport}
                                    disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                                >
                                    <FileText className="mr-2 h-4 w-4" />
                                    {exportMetadataMutation.isPending ? metadataActionText.exporting : metadataActionText.exportButton}
                                </Button>
                                <select
                                    aria-label={metadataActionText.formatLabel}
                                    value={metadataExportFormat}
                                    onChange={(event) => setMetadataExportFormat(event.target.value as TextExportFormat)}
                                    disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                                    className="border-input h-9 w-24 rounded-l-none rounded-r-md border bg-transparent px-2 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                                >
                                    <option value="json">JSON</option>
                                    <option value="pdf">PDF</option>
                                </select>
                            </div>
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={handleMetadataImportButtonClick}
                                disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                            >
                                <Upload className="mr-2 h-4 w-4" />
                                {importMetadataMutation.isPending ? metadataActionText.importing : metadataActionText.importButton}
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">{metadataActionText.hint}</p>
                    </div>
                    <PatientForm form={form} setForm={setForm} t={t} />
                    {formError && <p className="text-sm text-destructive">{formError}</p>}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateOpen(false)}>{t.cancel}</Button>
                        <Button onClick={submitCreate} disabled={isPending}>{createMutation.isPending ? t.creating : t.create}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!editPatient} onOpenChange={(open) => { if (!open) { setEditPatient(null); setFormError(null) } }}>
                <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
                    <DialogHeader><DialogTitle>{t.updatePatient}</DialogTitle></DialogHeader>
                    <div className="space-y-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                            <div className="flex w-full sm:w-auto">
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="rounded-r-none border-r-0"
                                    onClick={handleMetadataExport}
                                    disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                                >
                                    <FileText className="mr-2 h-4 w-4" />
                                    {exportMetadataMutation.isPending ? metadataActionText.exporting : metadataActionText.exportButton}
                                </Button>
                                <select
                                    aria-label={metadataActionText.formatLabel}
                                    value={metadataExportFormat}
                                    onChange={(event) => setMetadataExportFormat(event.target.value as TextExportFormat)}
                                    disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                                    className="border-input h-9 w-24 rounded-l-none rounded-r-md border bg-transparent px-2 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                                >
                                    <option value="json">JSON</option>
                                    <option value="pdf">PDF</option>
                                </select>
                            </div>
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={handleMetadataImportButtonClick}
                                disabled={exportMetadataMutation.isPending || importMetadataMutation.isPending}
                            >
                                <Upload className="mr-2 h-4 w-4" />
                                {importMetadataMutation.isPending ? metadataActionText.importing : metadataActionText.importButton}
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">{metadataActionText.hint}</p>
                    </div>
                    <PatientForm form={form} setForm={setForm} t={t} />
                    {formError && <p className="text-sm text-destructive">{formError}</p>}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditPatient(null)}>{t.cancel}</Button>
                        <Button onClick={submitUpdate} disabled={isPending || !editPatient}>{updateMutation.isPending ? t.saving : t.save}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!deletePatient} onOpenChange={(open) => { if (!open) setDeletePatient(null) }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t.deleteDialogTitle}</AlertDialogTitle>
                        <AlertDialogDescription>{t.deleteDialogDescription}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{t.cancel}</AlertDialogCancel>
                        <AlertDialogAction onClick={submitDelete} disabled={isPending}>{deleteMutation.isPending ? t.deleting : t.delete}</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}

function PatientForm({
    form,
    setForm,
    t,
}: {
    form: PatientFormState
    setForm: (value: PatientFormState) => void
    t: Translation
}) {
    const setValue = <K extends keyof PatientFormState>(field: K, value: PatientFormState[K]) => setForm({ ...form, [field]: value })
    return (
        <div className="grid gap-3 md:grid-cols-2">
            <Field label={t.fieldLabels.fullName}><Input value={form.full_name} onChange={(e) => setValue("full_name", e.target.value)} /></Field>
            <Field label={t.fieldLabels.dateOfBirth}><Input type="date" value={form.date_of_birth} onChange={(e) => setValue("date_of_birth", e.target.value)} /></Field>
            <Field label={t.fieldLabels.gender}>
                <select value={form.gender} onChange={(e) => setValue("gender", e.target.value as PatientFormState["gender"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">
                    {genderOptions.map((v) => <option key={v} value={v}>{t.genderLabels[v]}</option>)}
                </select>
            </Field>
            <Field label={t.fieldLabels.primaryPhone}><Input value={form.phone_primary} onChange={(e) => setValue("phone_primary", e.target.value)} /></Field>
            <Field label={t.fieldLabels.email}><Input type="email" value={form.email} onChange={(e) => setValue("email", e.target.value)} /></Field>
            <Field label={t.fieldLabels.ward}><Input value={form.address_ward} onChange={(e) => setValue("address_ward", e.target.value)} /></Field>
            <Field label={t.fieldLabels.district}><Input value={form.address_district} onChange={(e) => setValue("address_district", e.target.value)} /></Field>
            <Field label={t.fieldLabels.province}><Input value={form.address_province} onChange={(e) => setValue("address_province", e.target.value)} /></Field>
            <Field label={t.fieldLabels.emergencyContactName}><Input value={form.emergency_contact_name} onChange={(e) => setValue("emergency_contact_name", e.target.value)} /></Field>
            <Field label={t.fieldLabels.emergencyContactPhone}><Input value={form.emergency_contact_phone} onChange={(e) => setValue("emergency_contact_phone", e.target.value)} /></Field>
            <Field label={t.fieldLabels.emergencyRelationship}><Input value={form.emergency_contact_relationship} onChange={(e) => setValue("emergency_contact_relationship", e.target.value)} /></Field>
            <Field label={t.fieldLabels.triagePriority}>
                <select value={form.triage_priority} onChange={(e) => setValue("triage_priority", e.target.value as PatientFormState["triage_priority"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">
                    {triageOptions.map((v) => <option key={v} value={v}>{t.triageLabels[v]}</option>)}
                </select>
            </Field>
            <Field label={t.fieldLabels.profileStatus}>
                <select value={form.profile_status} onChange={(e) => setValue("profile_status", e.target.value as PatientFormState["profile_status"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">
                    {statusOptions.map((v) => <option key={v} value={v}>{t.statusLabels[v]}</option>)}
                </select>
            </Field>
        </div>
    )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
    return <div className="grid gap-2"><Label>{label}</Label>{children}</div>
}

function normalizeOptional(value: string): string | null {
    const normalized = value.trim()
    return normalized ? normalized : null
}

function formatDate(value: string | undefined, language: DashboardLanguage): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US")
}

function getGenderLabel(gender: string | null | undefined, labels: Translation["genderLabels"]): string {
    if (gender === "female" || gender === "male" || gender === "other") {
        return labels[gender]
    }
    return gender || "--"
}

function getPriorityLabel(priority: string | null | undefined, labels: Translation["priorityLabels"]): string {
    if (priority === "urgent" || priority === "high" || priority === "medium" || priority === "low") {
        return labels[priority]
    }
    return priority || "--"
}

function getErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object" && "message" in error) {
        const message = String((error as { message?: unknown }).message || "").trim()
        if (message) return message
    }
    return fallback
}

function triggerFileDownload(blob: Blob, fileName: string): void {
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = objectUrl
    anchor.download = fileName
    anchor.rel = "noopener"
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

function buildDownloadName(name: string | undefined, fallback: string, suffix = ""): string {
    const candidate = String(name || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")

    if (!candidate) {
        return fallback
    }

    const extension = fallback.includes(".") ? fallback.slice(fallback.lastIndexOf(".")) : ""
    if (!extension) {
        return `${candidate}${suffix}`
    }
    return `${candidate}${suffix}${extension}`
}
