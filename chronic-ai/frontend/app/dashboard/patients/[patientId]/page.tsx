/**
 * Patient detail page with profile photo upload
 */
"use client"

import { useRef, useState, type ChangeEvent } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@/contexts"
import { PageHeader, LoadingOverlay, RecordAIAnalysis, RecordDoctorComment } from "@/components/shared"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
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
import {
    usePatient,
    usePatientRecords,
    usePatientVitals,
    useCreateVitalSign,
    useUploadPatientPhoto,
    useUploadPatientRecordImage,
    useUpdatePatientRecord,
    useDeletePatientRecord,
} from "@/lib/hooks"
import type { MedicalRecord, MedicalRecordAIAnalysis, VitalSign, VitalSignInput } from "@/types"
import { Activity, ArrowLeft, FileText, Upload } from "lucide-react"
import { toast } from "sonner"

type ImagingRecordType =
    | "xray"
    | "ecg"
    | "ct"
    | "mri"

type VitalFormState = {
    recordedAt: string
    source: string
    bloodPressureSystolic: string
    bloodPressureDiastolic: string
    heartRate: string
    bloodGlucose: string
    bloodGlucoseTiming: string
    temperature: string
    oxygenSaturation: string
    weightKg: string
    notes: string
}

type RecordEditState = {
    recordId: string
    title: string
    recordType:
        | "prescription"
        | "lab"
        | "xray"
        | "ecg"
        | "ct"
        | "mri"
        | "notes"
        | "referral"
    doctorComment: string
    file: File | null
}

const imagingTypeOptions: Array<{ value: ImagingRecordType; label: string }> = [
    { value: "xray", label: "X-quang" },
    { value: "ecg", label: "Điện tâm đồ (ECG)" },
    { value: "ct", label: "CT" },
    { value: "mri", label: "MRI" },
]

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

const vitalSourceOptions = [
    { value: "self_reported", label: "Tự báo cáo" },
    { value: "clinic", label: "Phòng khám" },
    { value: "hospital", label: "Bệnh viện" },
    { value: "device", label: "Thiết bị" },
]

const glucoseTimingOptions = [
    { value: "", label: "Không rõ" },
    { value: "fasting", label: "Lúc đói" },
    { value: "before_meal", label: "Trước ăn" },
    { value: "after_meal", label: "Sau ăn" },
    { value: "random", label: "Ngẫu nhiên" },
]

export default function PatientDetailPage() {
    const router = useRouter()
    const { role, user } = useAuth()
    const params = useParams()
    const patientId = Array.isArray(params.patientId) ? params.patientId[0] : params.patientId

    const [recordFilter, setRecordFilter] = useState("")
    const [activeRecord, setActiveRecord] = useState<MedicalRecord | null>(null)

    const { data, isLoading, error } = usePatient(patientId ?? "")
    const {
        data: recordsData,
        isLoading: recordsLoading,
        error: recordsError,
        refetch: refetchRecords,
    } = usePatientRecords(patientId ?? "", recordFilter || undefined, 50)
    const { data: vitalsData, isLoading: vitalsLoading, error: vitalsError } = usePatientVitals(
        patientId ?? "",
        30
    )
    const photoUploadMutation = useUploadPatientPhoto()
    const recordUploadMutation = useUploadPatientRecordImage()
    const recordUpdateMutation = useUpdatePatientRecord()
    const recordDeleteMutation = useDeletePatientRecord()
    const createVitalMutation = useCreateVitalSign()

    const [photoFile, setPhotoFile] = useState<File | null>(null)
    const [photoError, setPhotoError] = useState<string | null>(null)
    const photoInputRef = useRef<HTMLInputElement>(null)

    const [recordFile, setRecordFile] = useState<File | null>(null)
    const [recordType, setRecordType] = useState<ImagingRecordType>("xray")
    const [recordTitle, setRecordTitle] = useState("")
    const [recordError, setRecordError] = useState<string | null>(null)
    const recordInputRef = useRef<HTMLInputElement>(null)
    const [postUploadRecordId, setPostUploadRecordId] = useState<string | null>(null)
    const [postUploadComment, setPostUploadComment] = useState("")
    const [postUploadAiAnalysis, setPostUploadAiAnalysis] = useState<MedicalRecordAIAnalysis | string | null>(null)
    const [isPostUploadDialogOpen, setIsPostUploadDialogOpen] = useState(false)

    const [editState, setEditState] = useState<RecordEditState | null>(null)
    const [editError, setEditError] = useState<string | null>(null)
    const [deleteRecord, setDeleteRecord] = useState<MedicalRecord | null>(null)
    const [recordListError, setRecordListError] = useState<string | null>(null)

    const [vitalForm, setVitalForm] = useState<VitalFormState>({
        recordedAt: "",
        source: role === "doctor" ? "clinic" : "self_reported",
        bloodPressureSystolic: "",
        bloodPressureDiastolic: "",
        heartRate: "",
        bloodGlucose: "",
        bloodGlucoseTiming: "",
        temperature: "",
        oxygenSaturation: "",
        weightKg: "",
        notes: "",
    })
    const [vitalError, setVitalError] = useState<string | null>(null)
    const [vitalSuccess, setVitalSuccess] = useState<string | null>(null)

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null
        setPhotoFile(selected)
        setPhotoError(null)
    }

    const handleUpload = () => {
        if (!patientId) {
            setPhotoError("Không tìm thấy mã bệnh nhân.")
            return
        }
        if (!photoFile) {
            setPhotoError("Vui lòng chọn ảnh trước khi tải lên.")
            return
        }
        if (!photoFile.type.startsWith("image/")) {
            setPhotoError("Tệp không hợp lệ. Vui lòng chọn ảnh.")
            return
        }

        photoUploadMutation.mutate(
            { patientId, file: photoFile },
            {
                onSuccess: () => {
                    setPhotoFile(null)
                    if (photoInputRef.current) {
                        photoInputRef.current.value = ""
                    }
                },
            }
        )
    }

    const handleRecordFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null
        setRecordFile(selected)
        setRecordError(null)
        setRecordListError(null)
    }

    const handleRecordUpload = () => {
        setRecordError(null)
        setRecordListError(null)
        if (!patientId) {
            setRecordError("Không tìm thấy mã bệnh nhân.")
            return
        }
        if (!recordFile) {
            setRecordError("Vui lòng chọn ảnh cận lâm sàng.")
            return
        }
        if (!recordFile.type.startsWith("image/")) {
            setRecordError("Tệp không hợp lệ. Vui lòng chọn ảnh.")
            return
        }

        recordUploadMutation.mutate(
            {
                patientId,
                recordType,
                file: recordFile,
                title: recordTitle.trim() || undefined,
            },
            {
                onSuccess: (response) => {
                    setRecordFile(null)
                    setRecordTitle("")
                    toast.success("Đã tải tệp thành công.")
                    setPostUploadRecordId(response.record_id)
                    setPostUploadComment("")
                    setPostUploadAiAnalysis(response.ai_analysis ?? null)
                    setIsPostUploadDialogOpen(true)
                    void refetchRecords()
                    if (recordInputRef.current) {
                        recordInputRef.current.value = ""
                    }
                },
            }
        )
    }

    const handlePostUploadCommentSave = () => {
        if (!patientId || !postUploadRecordId) {
            setIsPostUploadDialogOpen(false)
            return
        }

        recordUpdateMutation.mutate(
            {
                patientId,
                recordId: postUploadRecordId,
                doctorComment: postUploadComment,
            },
            {
                onSuccess: () => {
                    setIsPostUploadDialogOpen(false)
                    setPostUploadRecordId(null)
                    setPostUploadComment("")
                    setPostUploadAiAnalysis(null)
                    toast.success("Đã lưu nhận xét bác sĩ.")
                    void refetchRecords()
                },
                onError: (err) => {
                    setRecordError(getErrorMessage(err, "Không thể lưu nhận xét bác sĩ."))
                },
            }
        )
    }

    const openEditRecord = (record: MedicalRecord) => {
        setEditError(null)
        setRecordListError(null)
        setEditState({
            recordId: record.id,
            title: record.title || "",
            recordType: record.record_type,
            doctorComment: record.doctor_comment || "",
            file: null,
        })
    }

    const handleEditRecordFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        setEditState((prev) => {
            if (!prev) return prev
            return {
                ...prev,
                file: selected,
            }
        })
    }

    const handleRecordUpdate = () => {
        if (!patientId || !editState) {
            return
        }

        setEditError(null)
        setRecordListError(null)

        if (editState.file && !editState.file.type.startsWith("image/") && editState.file.type !== "application/pdf") {
            setEditError("Tệp thay thế phải là ảnh hoặc PDF.")
            return
        }

        recordUpdateMutation.mutate(
            {
                patientId,
                recordId: editState.recordId,
                title: editState.title,
                recordType: editState.recordType,
                doctorComment: editState.doctorComment,
                file: editState.file ?? undefined,
            },
            {
                onSuccess: () => {
                    setEditState(null)
                    setEditError(null)
                    toast.success("Đã cập nhật hồ sơ y khoa.")
                    if (activeRecord?.id === editState.recordId) {
                        setActiveRecord(null)
                    }
                    void refetchRecords()
                },
                onError: (err) => {
                    setEditError(getErrorMessage(err, "Cập nhật hồ sơ y khoa thất bại."))
                },
            }
        )
    }

    const handleDeleteRecord = () => {
        if (!patientId || !deleteRecord) {
            return
        }

        setRecordListError(null)

        recordDeleteMutation.mutate(
            {
                patientId,
                recordId: deleteRecord.id,
            },
            {
                onSuccess: () => {
                    if (activeRecord?.id === deleteRecord.id) {
                        setActiveRecord(null)
                    }
                    setDeleteRecord(null)
                    toast.success("Đã xóa hồ sơ y khoa thành công.")
                    void refetchRecords()
                },
                onError: (err) => {
                    setRecordListError(getErrorMessage(err, "Xóa hồ sơ y khoa thất bại."))
                },
            }
        )
    }

    const updateVitalForm = (key: keyof VitalFormState, value: string) => {
        setVitalForm(prev => ({
            ...prev,
            [key]: value,
        }))
    }

    const handleVitalSubmit = () => {
        setVitalError(null)
        setVitalSuccess(null)

        if (!patientId) {
            setVitalError("Không tìm thấy mã bệnh nhân.")
            return
        }

        const hasMeasurements = [
            vitalForm.bloodPressureSystolic,
            vitalForm.bloodPressureDiastolic,
            vitalForm.heartRate,
            vitalForm.bloodGlucose,
            vitalForm.temperature,
            vitalForm.oxygenSaturation,
            vitalForm.weightKg,
        ].some(value => value.trim() !== "")

        if (!hasMeasurements) {
            setVitalError("Vui lòng nhập ít nhất một chỉ số.")
            return
        }

        const payload: VitalSignInput = {
            recorded_at: vitalForm.recordedAt
                ? new Date(vitalForm.recordedAt).toISOString()
                : undefined,
            recorded_by: role === "doctor" ? user?.id : undefined,
            blood_pressure_systolic: vitalForm.bloodPressureSystolic
                ? Number.parseInt(vitalForm.bloodPressureSystolic, 10)
                : undefined,
            blood_pressure_diastolic: vitalForm.bloodPressureDiastolic
                ? Number.parseInt(vitalForm.bloodPressureDiastolic, 10)
                : undefined,
            heart_rate: vitalForm.heartRate
                ? Number.parseInt(vitalForm.heartRate, 10)
                : undefined,
            blood_glucose: vitalForm.bloodGlucose
                ? Number.parseFloat(vitalForm.bloodGlucose)
                : undefined,
            blood_glucose_timing: vitalForm.bloodGlucoseTiming
                ? (vitalForm.bloodGlucoseTiming as VitalSignInput["blood_glucose_timing"])
                : undefined,
            temperature: vitalForm.temperature
                ? Number.parseFloat(vitalForm.temperature)
                : undefined,
            oxygen_saturation: vitalForm.oxygenSaturation
                ? Number.parseInt(vitalForm.oxygenSaturation, 10)
                : undefined,
            weight_kg: vitalForm.weightKg
                ? Number.parseFloat(vitalForm.weightKg)
                : undefined,
            notes: vitalForm.notes.trim() || undefined,
            source: vitalForm.source
                ? (vitalForm.source as VitalSignInput["source"])
                : undefined,
        }

        createVitalMutation.mutate(
            { patientId, data: payload },
            {
                onSuccess: () => {
                    setVitalSuccess("Đã lưu chỉ số sinh tồn.")
                    setVitalForm({
                        recordedAt: "",
                        source: role === "doctor" ? "clinic" : "self_reported",
                        bloodPressureSystolic: "",
                        bloodPressureDiastolic: "",
                        heartRate: "",
                        bloodGlucose: "",
                        bloodGlucoseTiming: "",
                        temperature: "",
                        oxygenSaturation: "",
                        weightKg: "",
                        notes: "",
                    })
                },
            }
        )
    }

    if (isLoading) {
        return <LoadingOverlay text="Đang tải hồ sơ bệnh nhân..." />
    }

    if (error || !data?.patient) {
        return (
            <Card className="border-destructive/30 bg-destructive/5">
                <CardContent className="p-6 text-center">
                    <p className="text-destructive font-medium">Không thể tải hồ sơ bệnh nhân</p>
                    <p className="text-sm text-muted-foreground mt-1">
                        Vui lòng thử lại sau
                    </p>
                </CardContent>
            </Card>
        )
    }

    const patient = data.patient
    const initials = getInitials(patient.full_name)
    const vitals = vitalsData?.vitals ?? data.recent_vitals
    const postUploadRecord = postUploadRecordId
        ? recordsData?.records.find((record) => record.id === postUploadRecordId)
        : null
    const postUploadAnalysis = postUploadAiAnalysis ?? postUploadRecord?.analysis_result ?? null

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/patients")}>
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Quay lại
                </Button>
                <PageHeader title="Hồ sơ bệnh nhân" description={patient.full_name} />
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Ảnh hồ sơ</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center gap-4">
                        <Avatar className="h-16 w-16">
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
                        <div className="text-sm text-muted-foreground">
                            <p>{patient.full_name}</p>
                            <p>{patient.phone_primary}</p>
                        </div>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="patient-photo">Tải ảnh mới</Label>
                        <Input
                            id="patient-photo"
                            type="file"
                            accept="image/*"
                            onChange={handleFileChange}
                            ref={photoInputRef}
                        />
                    </div>

                    {photoError && (
                        <p className="text-sm text-destructive">{photoError}</p>
                    )}
                    {photoUploadMutation.isError && (
                        <p className="text-sm text-destructive">
                            Tải ảnh thất bại. Vui lòng thử lại.
                        </p>
                    )}
                    {photoUploadMutation.isSuccess && (
                        <p className="text-sm text-emerald-600">
                            Đã cập nhật ảnh hồ sơ.
                        </p>
                    )}

                    <Button
                        onClick={handleUpload}
                        disabled={!photoFile || photoUploadMutation.isPending}
                    >
                        <Upload className="h-4 w-4 mr-2" />
                        {photoUploadMutation.isPending ? "Đang tải..." : "Cập nhật ảnh"}
                    </Button>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Chỉ số sinh tồn</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="grid gap-6 lg:grid-cols-2">
                        <div className="space-y-4">
                            <div className="grid gap-3 md:grid-cols-2">
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-recorded-at">Thời gian đo</Label>
                                    <Input
                                        id="vital-recorded-at"
                                        type="datetime-local"
                                        value={vitalForm.recordedAt}
                                        onChange={(event) => updateVitalForm("recordedAt", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-source">Nguồn dữ liệu</Label>
                                    <select
                                        id="vital-source"
                                        value={vitalForm.source}
                                        onChange={(event) => updateVitalForm("source", event.target.value)}
                                        className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                    >
                                        {vitalSourceOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-bp-sys">Huyết áp tâm thu</Label>
                                    <Input
                                        id="vital-bp-sys"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="120"
                                        value={vitalForm.bloodPressureSystolic}
                                        onChange={(event) => updateVitalForm("bloodPressureSystolic", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-bp-dia">Huyết áp tâm trương</Label>
                                    <Input
                                        id="vital-bp-dia"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="80"
                                        value={vitalForm.bloodPressureDiastolic}
                                        onChange={(event) => updateVitalForm("bloodPressureDiastolic", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-heart-rate">Nhịp tim (bpm)</Label>
                                    <Input
                                        id="vital-heart-rate"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="72"
                                        value={vitalForm.heartRate}
                                        onChange={(event) => updateVitalForm("heartRate", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-spo2">SpO₂ (%)</Label>
                                    <Input
                                        id="vital-spo2"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="98"
                                        value={vitalForm.oxygenSaturation}
                                        onChange={(event) => updateVitalForm("oxygenSaturation", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-temperature">Nhiệt độ (°C)</Label>
                                    <Input
                                        id="vital-temperature"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="36.6"
                                        value={vitalForm.temperature}
                                        onChange={(event) => updateVitalForm("temperature", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-weight">Cân nặng (kg)</Label>
                                    <Input
                                        id="vital-weight"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="60"
                                        value={vitalForm.weightKg}
                                        onChange={(event) => updateVitalForm("weightKg", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-glucose">Đường huyết (mmol/L)</Label>
                                    <Input
                                        id="vital-glucose"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="5.6"
                                        value={vitalForm.bloodGlucose}
                                        onChange={(event) => updateVitalForm("bloodGlucose", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-glucose-timing">Thời điểm đo</Label>
                                    <select
                                        id="vital-glucose-timing"
                                        value={vitalForm.bloodGlucoseTiming}
                                        onChange={(event) => updateVitalForm("bloodGlucoseTiming", event.target.value)}
                                        className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                    >
                                        {glucoseTimingOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-notes">Ghi chú</Label>
                                    <Textarea
                                        id="vital-notes"
                                        placeholder="Nhập ghi chú nếu cần"
                                        value={vitalForm.notes}
                                        onChange={(event) => updateVitalForm("notes", event.target.value)}
                                        rows={3}
                                    />
                                </div>
                            </div>

                            {vitalError && (
                                <p className="text-sm text-destructive">{vitalError}</p>
                            )}
                            {createVitalMutation.isError && (
                                <p className="text-sm text-destructive">
                                    Lưu chỉ số thất bại. Vui lòng thử lại.
                                </p>
                            )}
                            {vitalSuccess && (
                                <p className="text-sm text-emerald-600">{vitalSuccess}</p>
                            )}

                            <Button
                                onClick={handleVitalSubmit}
                                disabled={createVitalMutation.isPending}
                            >
                                <Activity className="h-4 w-4 mr-2" />
                                {createVitalMutation.isPending ? "Đang lưu..." : "Lưu chỉ số"}
                            </Button>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-foreground">Lịch sử gần đây</p>
                                <Badge variant="secondary">{vitals?.length ?? 0} bản ghi</Badge>
                            </div>

                            {vitalsLoading && (!vitals || vitals.length === 0) && (
                                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                                    Đang tải dữ liệu sinh tồn...
                                </div>
                            )}

                            {vitalsError && (
                                <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                                    Không thể tải dữ liệu sinh tồn.
                                </div>
                            )}

                            {!vitalsLoading && !vitalsError && vitals && vitals.length === 0 && (
                                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                                    Chưa có chỉ số sinh tồn nào.
                                </div>
                            )}

                            {!vitalsError && vitals && vitals.length > 0 && (
                                <div className="space-y-3">
                                    {vitals.map((vital) => {
                                        const metrics = formatVitalMetrics(vital)
                                        return (
                                            <div key={vital.id} className="rounded-lg border p-4">
                                                <div className="flex items-start justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-medium text-foreground">
                                                            {formatDateTime(vital.recorded_at)}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">
                                                            {formatVitalSource(vital.source)}
                                                        </p>
                                                    </div>
                                                    {vital.source && (
                                                        <Badge variant="outline">
                                                            {formatVitalSource(vital.source)}
                                                        </Badge>
                                                    )}
                                                </div>
                                                {metrics.length > 0 && (
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        {metrics.map((metric) => (
                                                            <Badge key={metric} variant="secondary" className="text-xs">
                                                                {metric}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                                {vital.notes && (
                                                    <p className="mt-3 text-xs text-muted-foreground">
                                                        {vital.notes}
                                                    </p>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <CardTitle>Hồ sơ y khoa</CardTitle>
                        <p className="text-sm text-muted-foreground">
                            Xem và lọc các tài liệu đã tải lên
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
                    {recordListError && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                            {recordListError}
                        </div>
                    )}

                    {recordsLoading && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Đang tải hồ sơ y khoa...
                        </div>
                    )}

                    {recordsError && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                            Không thể tải hồ sơ y khoa.
                        </div>
                    )}

                    {!recordsLoading && !recordsError && recordsData?.records.length === 0 && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Chưa có hồ sơ y khoa nào.
                        </div>
                    )}

                    {!recordsLoading && !recordsError && recordsData && recordsData.records.length > 0 && (
                        <div className="space-y-3">
                            {recordsData.records.map((record) => (
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
                                            <RecordDoctorComment doctorComment={record.doctor_comment} />
                                            <RecordAIAnalysis analysis={record.analysis_result} />
                                        </div>
                                        <div className="flex flex-col gap-2 items-start md:items-end">
                                            {role === "doctor" && (
                                                <div className="flex w-full flex-wrap justify-end gap-2 pb-1">
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() => openEditRecord(record)}
                                                    >
                                                        Chỉnh sửa
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="destructive"
                                                        onClick={() => {
                                                            setRecordListError(null)
                                                            setDeleteRecord(record)
                                                        }}
                                                    >
                                                        Xóa
                                                    </Button>
                                                </div>
                                            )}
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

            <Card>
                <CardHeader>
                    <CardTitle>Ảnh cận lâm sàng</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-2">
                        <Label htmlFor="record-type">Loại ảnh</Label>
                        <select
                            id="record-type"
                            value={recordType}
                            onChange={(event) => {
                                setRecordType(event.target.value as ImagingRecordType)
                                setRecordError(null)
                            }}
                            className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                        >
                            {imagingTypeOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="record-title">Tiêu đề (tùy chọn)</Label>
                        <Input
                            id="record-title"
                            placeholder="Ví dụ: CT ngực 2026-02-01"
                            value={recordTitle}
                            onChange={(event) => {
                                setRecordTitle(event.target.value)
                            }}
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="record-image">Tải ảnh cận lâm sàng</Label>
                        <Input
                            id="record-image"
                            type="file"
                            accept="image/png,image/jpeg,image/jpg,image/bmp,image/tiff"
                            onChange={handleRecordFileChange}
                            ref={recordInputRef}
                        />
                    </div>

                    {recordError && (
                        <p className="text-sm text-destructive">{recordError}</p>
                    )}
                    {recordUploadMutation.isError && (
                        <p className="text-sm text-destructive">
                            Tải ảnh thất bại. Vui lòng thử lại.
                        </p>
                    )}

                    <Button
                        onClick={handleRecordUpload}
                        disabled={!recordFile || recordUploadMutation.isPending}
                    >
                        <Upload className="h-4 w-4 mr-2" />
                        {recordUploadMutation.isPending ? "Đang tải..." : "Tải ảnh cận lâm sàng"}
                    </Button>
                </CardContent>
            </Card>

            <Dialog
                open={isPostUploadDialogOpen}
                onOpenChange={(open) => {
                    setIsPostUploadDialogOpen(open)
                    if (!open) {
                        setPostUploadRecordId(null)
                        setPostUploadComment("")
                        setPostUploadAiAnalysis(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Thêm nhận xét bác sĩ (tùy chọn)</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            AI đã phân tích xong. Bạn có thể bổ sung nhận xét bác sĩ cho hồ sơ này.
                        </p>
                        {postUploadAnalysis ? (
                            <RecordAIAnalysis analysis={postUploadAnalysis} />
                        ) : (
                            <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
                                Chưa có nội dung phân tích AI để tham khảo.
                            </div>
                        )}
                        <Textarea
                            value={postUploadComment}
                            onChange={(event) => setPostUploadComment(event.target.value)}
                            placeholder="Nhập nhận xét bác sĩ..."
                            rows={4}
                        />
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setIsPostUploadDialogOpen(false)
                                setPostUploadRecordId(null)
                                setPostUploadComment("")
                                setPostUploadAiAnalysis(null)
                            }}
                        >
                            Bỏ qua
                        </Button>
                        <Button
                            onClick={handlePostUploadCommentSave}
                            disabled={!postUploadRecordId || recordUpdateMutation.isPending}
                        >
                            {recordUpdateMutation.isPending ? "Đang lưu..." : "Lưu nhận xét"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog
                open={!!editState}
                onOpenChange={(open) => {
                    if (!open) {
                        setEditState(null)
                        setEditError(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-xl">
                    <DialogHeader>
                        <DialogTitle>Cập nhật hồ sơ y khoa</DialogTitle>
                    </DialogHeader>
                    {editState && (
                        <div className="space-y-4">
                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-title">Tiêu đề</Label>
                                <Input
                                    id="edit-record-title"
                                    value={editState.title}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    title: event.target.value,
                                                }
                                                : prev
                                        )
                                    }
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-type">Loại hồ sơ</Label>
                                <select
                                    id="edit-record-type"
                                    value={editState.recordType}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    recordType: event.target.value as RecordEditState["recordType"],
                                                }
                                                : prev
                                        )
                                    }
                                    className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                >
                                    {recordTypeOptions
                                        .filter((option) => option.value !== "")
                                        .map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                </select>
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-file">Thay tệp (tùy chọn)</Label>
                                <Input
                                    id="edit-record-file"
                                    type="file"
                                    accept="image/png,image/jpeg,image/jpg,image/bmp,image/tiff,application/pdf"
                                    onChange={handleEditRecordFileChange}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Nếu thay tệp, hệ thống sẽ chạy lại phân tích AI.
                                </p>
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-comment">Nhận xét bác sĩ</Label>
                                <Textarea
                                    id="edit-record-comment"
                                    value={editState.doctorComment}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    doctorComment: event.target.value,
                                                }
                                                : prev
                                        )
                                    }
                                    rows={4}
                                    placeholder="Nhập nhận xét bác sĩ..."
                                />
                            </div>

                            {editError && <p className="text-sm text-destructive">{editError}</p>}
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditState(null)}>
                            Hủy
                        </Button>
                        <Button onClick={handleRecordUpdate} disabled={!editState || recordUpdateMutation.isPending}>
                            {recordUpdateMutation.isPending ? "Đang cập nhật..." : "Lưu thay đổi"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog
                open={!!deleteRecord}
                onOpenChange={(open) => {
                    if (!open) {
                        setDeleteRecord(null)
                    }
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Xóa hồ sơ y khoa?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Tệp, kết quả phân tích AI và dữ liệu liên quan của bản ghi này sẽ bị xóa.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Hủy</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteRecord}
                            disabled={recordDeleteMutation.isPending}
                        >
                            {recordDeleteMutation.isPending ? "Đang xóa..." : "Xóa"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

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
                            <RecordDoctorComment doctorComment={activeRecord.doctor_comment} />
                            <RecordAIAnalysis analysis={activeRecord.analysis_result} />
                        </div>
                    ) : (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            Không có ảnh để hiển thị
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    )
}

function getInitials(name: string): string {
    return name
        .split(" ")
        .map(word => word[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
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

function formatVitalMetrics(vital: VitalSign): string[] {
    const metrics: string[] = []

    if (vital.blood_pressure_systolic || vital.blood_pressure_diastolic) {
        const systolic = vital.blood_pressure_systolic ?? "--"
        const diastolic = vital.blood_pressure_diastolic ?? "--"
        metrics.push(`HA ${systolic}/${diastolic} mmHg`)
    }
    if (vital.heart_rate) {
        metrics.push(`Mạch ${vital.heart_rate} bpm`)
    }
    if (vital.blood_glucose) {
        const timingLabel = formatGlucoseTiming(vital.blood_glucose_timing)
        metrics.push(`Đường huyết ${vital.blood_glucose} mmol/L${timingLabel ? ` (${timingLabel})` : ""}`)
    }
    if (vital.temperature) {
        metrics.push(`Nhiệt độ ${vital.temperature} °C`)
    }
    if (vital.oxygen_saturation) {
        metrics.push(`SpO₂ ${vital.oxygen_saturation}%`)
    }
    if (vital.weight_kg) {
        metrics.push(`Cân nặng ${vital.weight_kg} kg`)
    }

    return metrics
}

function formatVitalSource(source?: VitalSign["source"]): string {
    switch (source) {
        case "self_reported":
            return "Tự báo cáo"
        case "clinic":
            return "Phòng khám"
        case "hospital":
            return "Bệnh viện"
        case "device":
            return "Thiết bị"
        default:
            return "Không rõ"
    }
}

function formatGlucoseTiming(timing?: VitalSign["blood_glucose_timing"]): string {
    switch (timing) {
        case "fasting":
            return "lúc đói"
        case "before_meal":
            return "trước ăn"
        case "after_meal":
            return "sau ăn"
        case "random":
            return "ngẫu nhiên"
        default:
            return ""
    }
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

function getErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object" && "message" in error) {
        const message = String((error as { message?: unknown }).message || "").trim()
        if (message) return message
    }
    return fallback
}

