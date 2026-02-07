/**
 * Patient API functions
 */

import { apiClient } from "./client"
import type {
    Patient,
    PatientListResponse,
    PatientDetailResponse,
    MedicalRecordsResponse,
    DashboardStats,
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
 * Get dashboard statistics
 */
export async function getDashboardStats(doctorId?: string): Promise<DashboardStats> {
    const endpoint = doctorId
        ? `/doctor/stats?doctor_id=${doctorId}`
        : "/doctor/stats"

    return apiClient<DashboardStats>(endpoint)
}
