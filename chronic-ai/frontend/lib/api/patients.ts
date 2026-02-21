/**
 * Patient API functions
 */

import { apiClient, downloadFile, uploadFile } from "./client"
import type {
    DeletePatientResponse,
    PatientListResponse,
    PatientDetailResponse,
    PatientCreateInput,
    PatientMutationResponse,
    PatientUpdateInput,
    MedicalRecordsResponse,
    DashboardStats,
    PatientPhotoUploadResponse,
    UploadResponse,
    PatientTextImportStartResponse,
    PatientTextImportStatusResponse,
    VitalSignCreateResponse,
    PatientTextImportResponse,
    PatientMetadataImportPreview,
    PatientMetadataImportPreviewResponse,
    VitalSignInput,
    VitalSignsResponse,
    VitalImportPreviewResponse,
} from "@/types"

interface ListPatientsParams {
    page?: number
    pageSize?: number
    status?: string
    priority?: string
    search?: string
}

/**
 * Get paginated list of patients
 */
export async function getPatients(params: ListPatientsParams = {}): Promise<PatientListResponse> {
    const searchParams = new URLSearchParams()

    if (params.page) searchParams.set("page", params.page.toString())
    if (params.pageSize) searchParams.set("page_size", params.pageSize.toString())
    if (params.status) searchParams.set("status", params.status)
    if (params.priority) searchParams.set("priority", params.priority)
    if (params.search) searchParams.set("search", params.search)

    const queryString = searchParams.toString()
    const endpoint = `/doctor/patients${queryString ? `?${queryString}` : ""}`

    return apiClient<PatientListResponse>(endpoint)
}

/**
 * Get detailed patient information with vitals and consultations
 */
export async function getPatientDetail(patientId: string): Promise<PatientDetailResponse> {
    return apiClient<PatientDetailResponse>(`/doctor/patients/${patientId}`)
}

/**
 * Create patient profile (general patient info only)
 */
export async function createPatient(payload: PatientCreateInput): Promise<PatientMutationResponse> {
    return apiClient<PatientMutationResponse>("/doctor/patients", {
        method: "POST",
        body: JSON.stringify(payload),
    })
}

/**
 * Update patient profile (general patient info only)
 */
export async function updatePatient(
    patientId: string,
    payload: PatientUpdateInput
): Promise<PatientMutationResponse> {
    return apiClient<PatientMutationResponse>(`/doctor/patients/${patientId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    })
}

/**
 * Delete patient profile
 */
export async function deletePatient(patientId: string): Promise<DeletePatientResponse> {
    return apiClient<DeletePatientResponse>(`/doctor/patients/${patientId}`, {
        method: "DELETE",
    })
}

/**
 * Get medical records for a patient
 */
export async function getPatientRecords(
    patientId: string,
    recordType?: string,
    limit?: number
): Promise<MedicalRecordsResponse> {
    const searchParams = new URLSearchParams()

    if (recordType) searchParams.set("record_type", recordType)
    if (limit) searchParams.set("limit", limit.toString())

    const queryString = searchParams.toString()
    const endpoint = `/doctor/patients/${patientId}/records${queryString ? `?${queryString}` : ""}`

    return apiClient<MedicalRecordsResponse>(endpoint)
}

/**
 * Get vital signs for a patient
 */
export async function getPatientVitals(
    patientId: string,
    limit = 30
): Promise<VitalSignsResponse> {
    const endpoint = `/doctor/patients/${patientId}/vitals?limit=${limit}`
    return apiClient<VitalSignsResponse>(endpoint)
}

/**
 * Create a new vital sign entry
 */
export async function createPatientVital(
    patientId: string,
    payload: VitalSignInput
): Promise<VitalSignCreateResponse> {
    return apiClient<VitalSignCreateResponse>(`/doctor/patients/${patientId}/vitals`, {
        method: "POST",
        body: JSON.stringify(payload),
    })
}

/**
 * Get dashboard statistics
 */
export async function getDashboardStats(doctorId?: string): Promise<DashboardStats> {
    const endpoint = doctorId
        ? `/doctor/stats?doctor_id=${doctorId}`
        : "/doctor/stats"

    return apiClient<DashboardStats>(endpoint)
}

/**
 * Upload a patient profile photo
 */
export async function uploadPatientPhoto(
    patientId: string,
    file: File
): Promise<PatientPhotoUploadResponse> {
    const formData = new FormData()
    formData.append("patient_id", patientId)
    formData.append("file", file)

    return uploadFile<PatientPhotoUploadResponse>("/upload/patient-photo", formData)
}

/**
 * Upload a patient ECG/X-ray image as a medical record
 */
export async function uploadPatientRecordImage(
    patientId: string,
    recordType:
        | "xray"
        | "ecg"
        | "ct"
        | "mri",
    file: File,
    title?: string,
    doctorComment?: string
): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append("patient_id", patientId)
    formData.append("record_type", recordType)
    formData.append("file", file)
    if (title) formData.append("title", title)
    if (doctorComment !== undefined) formData.append("doctor_comment", doctorComment)

    return uploadFile<UploadResponse>("/upload/patient-record-image", formData)
}

interface UpdatePatientRecordInput {
    patientId: string
    recordId: string
    doctorComment?: string
    title?: string
    recordType?: "prescription" | "lab" | "xray" | "ecg" | "ct" | "mri" | "notes" | "referral"
    file?: File
}

export async function updatePatientRecord(input: UpdatePatientRecordInput): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append("patient_id", input.patientId)
    if (input.doctorComment !== undefined) formData.append("doctor_comment", input.doctorComment)
    if (input.title !== undefined) formData.append("title", input.title)
    if (input.recordType) formData.append("record_type", input.recordType)
    if (input.file) formData.append("file", input.file)

    return uploadFile<UploadResponse>(`/upload/patient-record/${input.recordId}`, formData, "PUT")
}

export async function deletePatientRecord(patientId: string, recordId: string): Promise<{ status: string; record_id: string; patient_id: string; message: string }> {
    const endpoint = `/upload/patient-record/${recordId}?patient_id=${encodeURIComponent(patientId)}`
    return apiClient<{ status: string; record_id: string; patient_id: string; message: string }>(endpoint, {
        method: "DELETE",
    })
}

/**
 * Export full patient record ZIP (text payload + medical files).
 */
export async function exportPatientText(
    patientId: string,
    format: "json" | "pdf" = "json",
    language: "vi" | "en" = "en"
) {
    const endpoint = `/doctor/patients/${patientId}/export?format=${encodeURIComponent(format)}&lang=${encodeURIComponent(language)}`
    return downloadFile(endpoint)
}

/**
 * Export vital-sign data (sub-data scope).
 */
export async function exportPatientVitals(
    patientId: string,
    format: "json" | "pdf" = "json",
    language: "vi" | "en" = "en"
) {
    const endpoint = `/doctor/patients/${patientId}/vitals/export?format=${encodeURIComponent(format)}&lang=${encodeURIComponent(language)}`
    return downloadFile(endpoint)
}

/**
 * Import vital-sign data for preview/prefill only (no DB write).
 */
export async function importPatientVitalsPreview(
    patientId: string,
    file: File
): Promise<VitalImportPreviewResponse> {
    const formData = new FormData()
    formData.append("file", file)
    const endpoint = `/doctor/patients/${patientId}/vitals/import/preview`
    return uploadFile<VitalImportPreviewResponse>(endpoint, formData, "POST")
}

/**
 * Export patient metadata from form payload.
 */
export async function exportPatientMetadata(
    metadata: PatientMetadataImportPreview,
    format: "json" | "pdf" = "json",
    language: "vi" | "en" = "en"
) {
    const endpoint = `/doctor/patient-metadata/export?format=${encodeURIComponent(format)}&lang=${encodeURIComponent(language)}`
    return downloadFile(endpoint, {
        method: "POST",
        body: JSON.stringify({ metadata }),
        headers: {
            "Content-Type": "application/json",
        },
    })
}

/**
 * Import patient metadata for preview/prefill only (no DB write).
 */
export async function importPatientMetadataPreview(
    file: File
): Promise<PatientMetadataImportPreviewResponse> {
    const formData = new FormData()
    formData.append("file", file)
    const endpoint = "/doctor/patient-metadata/import/preview"
    return uploadFile<PatientMetadataImportPreviewResponse>(endpoint, formData, "POST")
}

/**
 * Legacy endpoint: export original patient record files as ZIP.
 * Kept for backward compatibility.
 */
export async function exportPatientFiles(patientId: string) {
    const endpoint = `/doctor/patients/${patientId}/export/files`
    return downloadFile(endpoint)
}

/**
 * Import full patient record from exported ZIP.
 */
export async function importPatientText(patientId: string, file: File): Promise<PatientTextImportResponse> {
    const start = await startPatientTextImport(patientId, file)
    while (true) {
        await new Promise((resolve) => setTimeout(resolve, 900))
        const status = await getPatientTextImportStatus(patientId, start.job_id)
        if (status.status === "completed") {
            if (!status.result) {
                throw new Error("Import completed without result payload.")
            }
            return status.result
        }
        if (status.status === "failed") {
            throw new Error(status.error || "Patient import failed.")
        }
    }
}

export async function startPatientTextImport(
    patientId: string,
    file: File
): Promise<PatientTextImportStartResponse> {
    const formData = new FormData()
    formData.append("file", file)
    const endpoint = `/doctor/patients/${patientId}/import`
    return uploadFile<PatientTextImportStartResponse>(endpoint, formData, "POST")
}

export async function getPatientTextImportStatus(
    patientId: string,
    jobId: string
): Promise<PatientTextImportStatusResponse> {
    const endpoint = `/doctor/patients/${patientId}/import/${jobId}`
    return apiClient<PatientTextImportStatusResponse>(endpoint)
}

/**
 * Generate an AI clinical summary for a patient profile
 */
export async function getPatientSummary(
    patientId: string
): Promise<import("@/types").PatientSummaryResponse> {
    return apiClient<import("@/types").PatientSummaryResponse>(
        `/doctor/patients/${patientId}/summary`,
        { timeout: 120000 }
    )
}
