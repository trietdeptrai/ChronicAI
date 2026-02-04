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
import { usePatient, useUploadPatientPhoto } from "@/lib/hooks"
import { ArrowLeft, Upload } from "lucide-react"

export default function PatientDetailPage() {
    const router = useRouter()
    const params = useParams()
    const patientId = Array.isArray(params.patientId) ? params.patientId[0] : params.patientId

    const { data, isLoading, error } = usePatient(patientId ?? "")
    const uploadMutation = useUploadPatientPhoto()

    const [file, setFile] = useState<File | null>(null)
    const [localError, setLocalError] = useState<string | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null
        setFile(selected)
        setLocalError(null)
    }

    const handleUpload = () => {
        if (!patientId) {
            setLocalError("Không tìm thấy mã bệnh nhân.")
            return
        }
        if (!file) {
            setLocalError("Vui lòng chọn ảnh trước khi tải lên.")
            return
        }
        if (!file.type.startsWith("image/")) {
            setLocalError("Tệp không hợp lệ. Vui lòng chọn ảnh.")
            return
        }

        uploadMutation.mutate(
            { patientId, file },
            {
                onSuccess: () => {
                    setFile(null)
                    if (inputRef.current) {
                        inputRef.current.value = ""
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
                            ref={inputRef}
                        />
                    </div>

                    {localError && (
                        <p className="text-sm text-destructive">{localError}</p>
                    )}
                    {uploadMutation.isError && (
                        <p className="text-sm text-destructive">
                            Tải ảnh thất bại. Vui lòng thử lại.
                        </p>
                    )}
                    {uploadMutation.isSuccess && (
                        <p className="text-sm text-emerald-600">
                            Đã cập nhật ảnh hồ sơ.
                        </p>
                    )}

                    <Button
                        onClick={handleUpload}
                        disabled={!file || uploadMutation.isPending}
                    >
                        <Upload className="h-4 w-4 mr-2" />
                        {uploadMutation.isPending ? "Đang tải..." : "Cập nhật ảnh"}
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
