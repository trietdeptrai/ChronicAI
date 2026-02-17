/**
 * TanStack Query hooks for patient data
 */
"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
    createPatient,
    deletePatient,
    getPatients,
    getPatientDetail,
    getPatientRecords,
    getDashboardStats,
    uploadPatientPhoto,
    uploadPatientRecordImage,
    updatePatient,
    updatePatientRecord,
    deletePatientRecord,
    getPatientVitals,
    createPatientVital,
} from "@/lib/api"
import type {
    DeletePatientResponse,
    PatientListResponse,
    PatientDetailResponse,
    PatientCreateInput,
    PatientMutationResponse,
    PatientUpdateInput,
    MedicalRecordsResponse,
    DashboardStats,
    VitalSignsResponse,
    VitalSignCreateResponse,
    VitalSignInput,
} from "@/types"

interface UsePatientParams {
    page?: number
    pageSize?: number
    status?: string
    priority?: string
    search?: string
}

/**
 * Hook for fetching paginated patient list
 */
export function usePatients(params: UsePatientParams = {}) {
    return useQuery<PatientListResponse>({
        queryKey: ["patients", params],
        queryFn: () => getPatients(params),
    })
}

/**
 * Hook for fetching single patient with details
 */
export function usePatient(patientId: string) {
    return useQuery<PatientDetailResponse>({
        queryKey: ["patients", patientId],
        queryFn: () => getPatientDetail(patientId),
        enabled: !!patientId,
    })
}

/**
 * Hook for fetching patient medical records
 */
export function usePatientRecords(patientId: string, recordType?: string, limit?: number) {
    return useQuery<MedicalRecordsResponse>({
        queryKey: ["patients", patientId, "records", recordType, limit],
        queryFn: () => getPatientRecords(patientId, recordType, limit),
        enabled: !!patientId,
    })
}

/**
 * Hook for fetching patient vital signs
 */
export function usePatientVitals(patientId: string, limit = 30) {
    return useQuery<VitalSignsResponse>({
        queryKey: ["patients", patientId, "vitals", limit],
        queryFn: () => getPatientVitals(patientId, limit),
        enabled: !!patientId,
    })
}

/**
 * Hook for fetching dashboard statistics
 */
export function useDashboardStats(doctorId?: string) {
    return useQuery<DashboardStats>({
        queryKey: ["dashboard-stats", doctorId],
        queryFn: () => getDashboardStats(doctorId),
        refetchInterval: 60000, // Refresh every minute
    })
}

/**
 * Hook to invalidate patient-related queries
 */
export function useInvalidatePatients() {
    const queryClient = useQueryClient()

    return {
        invalidateList: () => queryClient.invalidateQueries({ queryKey: ["patients"] }),
        invalidateDetail: (patientId: string) =>
            queryClient.invalidateQueries({ queryKey: ["patients", patientId] }),
        invalidateAll: () => queryClient.invalidateQueries({ queryKey: ["patients"] }),
    }
}

/**
 * Hook for creating patient profile info
 */
export function useCreatePatient() {
    const queryClient = useQueryClient()

    return useMutation<PatientMutationResponse, Error, PatientCreateInput>({
        mutationFn: createPatient,
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["patients"] })
            queryClient.invalidateQueries({ queryKey: ["patients", data.patient.id] })
            queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
        },
    })
}

/**
 * Hook for updating patient profile info
 */
export function useUpdatePatient() {
    const queryClient = useQueryClient()

    return useMutation<PatientMutationResponse, Error, { patientId: string; data: PatientUpdateInput }>({
        mutationFn: ({ patientId, data }) => updatePatient(patientId, data),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["patients"] })
            queryClient.invalidateQueries({ queryKey: ["patients", data.patient.id] })
            queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
        },
    })
}

/**
 * Hook for deleting patient profile info
 */
export function useDeletePatientProfile() {
    const queryClient = useQueryClient()

    return useMutation<DeletePatientResponse, Error, { patientId: string }>({
        mutationFn: ({ patientId }) => deletePatient(patientId),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients"] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
            queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
        },
    })
}

/**
 * Hook for uploading patient profile photo
 */
export function useUploadPatientPhoto() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ patientId, file }: { patientId: string; file: File }) =>
            uploadPatientPhoto(patientId, file),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients"] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
        },
    })
}

/**
 * Hook for uploading patient ECG/X-ray images
 */
export function useUploadPatientRecordImage() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({
            patientId,
            recordType,
            file,
            title,
            doctorComment,
        }: {
            patientId: string
            recordType:
                | "xray"
                | "ecg"
                | "ct"
                | "mri"
            file: File
            title?: string
            doctorComment?: string
        }) => uploadPatientRecordImage(patientId, recordType, file, title, doctorComment),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId, "records"] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
        },
    })
}

export function useUpdatePatientRecord() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: updatePatientRecord,
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId, "records"] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
        },
    })
}

export function useDeletePatientRecord() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ patientId, recordId }: { patientId: string; recordId: string }) =>
            deletePatientRecord(patientId, recordId),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId, "records"] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
        },
    })
}

/**
 * Hook for creating a new vital sign entry
 */
export function useCreateVitalSign() {
    const queryClient = useQueryClient()

    return useMutation<VitalSignCreateResponse, Error, { patientId: string; data: VitalSignInput }>({
        mutationFn: ({ patientId, data }) => createPatientVital(patientId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId] })
            queryClient.invalidateQueries({ queryKey: ["patients", variables.patientId, "vitals"] })
        },
    })
}
