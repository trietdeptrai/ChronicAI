/**
 * Appointment API functions
 */

import { apiClient } from "./client"
import type {
    AppointmentDecisionInput,
    AppointmentMutationResponse,
    AppointmentRemindersResponse,
    AppointmentRequestInput,
    AppointmentStatus,
    DoctorAppointmentsResponse,
    PatientAppointmentsResponse,
} from "@/types"

interface AppointmentQueryParams {
    start?: string
    end?: string
    status?: AppointmentStatus
}

export async function requestAppointment(
    payload: AppointmentRequestInput
): Promise<AppointmentMutationResponse> {
    return apiClient<AppointmentMutationResponse>("/appointments/request", {
        method: "POST",
        body: JSON.stringify(payload),
    })
}

export async function getPatientAppointments(
    patientId: string,
    params: AppointmentQueryParams = {}
): Promise<PatientAppointmentsResponse> {
    const searchParams = new URLSearchParams()
    if (params.start) searchParams.set("start", params.start)
    if (params.end) searchParams.set("end", params.end)
    if (params.status) searchParams.set("status", params.status)

    const queryString = searchParams.toString()
    const endpoint = `/appointments/patient/${patientId}${queryString ? `?${queryString}` : ""}`
    return apiClient<PatientAppointmentsResponse>(endpoint)
}

export async function getDoctorAppointments(
    doctorId: string,
    params: AppointmentQueryParams = {}
): Promise<DoctorAppointmentsResponse> {
    const searchParams = new URLSearchParams()
    if (params.start) searchParams.set("start", params.start)
    if (params.end) searchParams.set("end", params.end)
    if (params.status) searchParams.set("status", params.status)

    const queryString = searchParams.toString()
    const endpoint = `/appointments/doctor/${doctorId}${queryString ? `?${queryString}` : ""}`
    return apiClient<DoctorAppointmentsResponse>(endpoint)
}

export async function decideAppointment(
    appointmentId: string,
    payload: AppointmentDecisionInput
): Promise<AppointmentMutationResponse> {
    return apiClient<AppointmentMutationResponse>(`/appointments/${appointmentId}/decision`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    })
}

export async function getPatientAppointmentReminders(
    patientId: string,
    withinHours = 48
): Promise<AppointmentRemindersResponse> {
    return apiClient<AppointmentRemindersResponse>(
        `/appointments/patient/${patientId}/reminders?within_hours=${withinHours}`
    )
}
