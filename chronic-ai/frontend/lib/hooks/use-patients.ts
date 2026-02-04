/**
 * TanStack Query hooks for patient data
 */
"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
    getPatients,
    getPatientDetail,
    getPatientRecords,
    getDashboardStats,
    uploadPatientPhoto,
} from "@/lib/api"
import type { PatientListResponse, PatientDetailResponse, MedicalRecordsResponse, DashboardStats } from "@/types"

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
