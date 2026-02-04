/**
 * Patient detail page with profile photo upload
 */
"use client"

import { useRef, useState, type ChangeEvent } from "react"
import { useParams, useRouter } from "next/navigation"
import { PageHeader, LoadingOverlay } from "@/components/shared"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { usePatient, useUploadPatientPhoto, useUploadPatientRecordImage } from "@/lib/hooks"
import { ArrowLeft, Upload } from "lucide-react"

type ImagingRecordType =
    | "xray"
    | "ecg"
    | "ct"
    | "mri"

const imagingTypeOptions: Array<{ value: ImagingRecordType; label: string }> = [
    { value: "xray", label: "X-quang" },
    { value: "ecg", label: "Điện tâm đồ (ECG)" },
    { value: "ct", label: "CT" },
    { value: "mri", label: "MRI" },
]

export default function PatientDetailPage() {
    const router = useRouter()
    const params = useParams()
    const patientId = Array.isArray(params.patientId) ? params.patientId[0] : params.patientId

    const { data, isLoading, error } = usePatient(patientId ?? "")
    const photoUploadMutation = useUploadPatientPhoto()
    const recordUploadMutation = useUploadPatientRecordImage()

    const [photoFile, setPhotoFile] = useState<File | null>(null)
    const [photoError, setPhotoError] = useState<string | null>(null)
    const photoInputRef = useRef<HTMLInputElement>(null)

    const [recordFile, setRecordFile] = useState<File | null>(null)
    const [recordType, setRecordType] = useState<ImagingRecordType>("xray")
    const [recordTitle, setRecordTitle] = useState("")
    const [recordError, setRecordError] = useState<string | null>(null)
    const [recordSuccess, setRecordSuccess] = useState<string | null>(null)
    const recordInputRef = useRef<HTMLInputElement>(null)

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
        setRecordSuccess(null)
    }

    const handleRecordUpload = () => {
        setRecordError(null)
        setRecordSuccess(null)
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
                onSuccess: () => {
                    setRecordFile(null)
                    setRecordTitle("")
                    setRecordSuccess("Đã tải ảnh cận lâm sàng thành công.")
                    if (recordInputRef.current) {
                        recordInputRef.current.value = ""
                    }
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
                                setRecordSuccess(null)
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
                        <Label htmlFor="record-title">Tiêu đề (tuỳ chọn)</Label>
                        <Input
                            id="record-title"
                            placeholder="Ví dụ: CT ngực 2026-02-01"
                            value={recordTitle}
                            onChange={(event) => {
                                setRecordTitle(event.target.value)
                                setRecordSuccess(null)
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
                    {recordSuccess && (
                        <p className="text-sm text-emerald-600">{recordSuccess}</p>
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
