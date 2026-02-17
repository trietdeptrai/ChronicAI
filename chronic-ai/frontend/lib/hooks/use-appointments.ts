/**
 * TanStack Query hooks for appointment booking workflows.
 */
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
    decideAppointment,
    getDoctorAppointments,
    getPatientAppointmentReminders,
    getPatientAppointments,
    requestAppointment,
} from "@/lib/api"
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

export function usePatientAppointments(
    patientId: string,
    params: AppointmentQueryParams = {},
    enabled = true
) {
    return useQuery<PatientAppointmentsResponse>({
        queryKey: ["appointments", "patient", patientId, params],
        queryFn: () => getPatientAppointments(patientId, params),
        enabled: enabled && !!patientId,
    })
}

export function useDoctorAppointments(
    doctorId: string,
    params: AppointmentQueryParams = {},
    enabled = true
) {
    return useQuery<DoctorAppointmentsResponse>({
        queryKey: ["appointments", "doctor", doctorId, params],
        queryFn: () => getDoctorAppointments(doctorId, params),
        enabled: enabled && !!doctorId,
    })
}

export function usePatientAppointmentReminders(
    patientId: string,
    withinHours = 48,
    enabled = true
) {
    return useQuery<AppointmentRemindersResponse>({
        queryKey: ["appointments", "reminders", patientId, withinHours],
        queryFn: () => getPatientAppointmentReminders(patientId, withinHours),
        enabled: enabled && !!patientId,
        refetchInterval: 60_000,
    })
}

export function useRequestAppointment() {
    const queryClient = useQueryClient()

    return useMutation<AppointmentMutationResponse, Error, AppointmentRequestInput>({
        mutationFn: requestAppointment,
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({
                queryKey: ["appointments", "patient", variables.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["appointments", "doctor", data.appointment.doctor_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["appointments", "reminders", variables.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["patients", variables.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["patients"],
            })
        },
    })
}

export function useDecideAppointment() {
    const queryClient = useQueryClient()

    return useMutation<
        AppointmentMutationResponse,
        Error,
        { appointmentId: string; payload: AppointmentDecisionInput }
    >({
        mutationFn: ({ appointmentId, payload }) => decideAppointment(appointmentId, payload),
        onSuccess: (data) => {
            const appointment = data.appointment
            queryClient.invalidateQueries({
                queryKey: ["appointments", "doctor", appointment.doctor_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["appointments", "patient", appointment.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["appointments", "reminders", appointment.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["patients", appointment.patient_id],
            })
            queryClient.invalidateQueries({
                queryKey: ["patients"],
            })
        },
    })
}
