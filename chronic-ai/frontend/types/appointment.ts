export type AppointmentStatus =
    | "pending"
    | "accepted"
    | "rejected"
    | "cancelled"
    | "completed"

export type AppointmentType =
    | "follow_up"
    | "routine_check"
    | "new_symptom"
    | "medication_review"
    | "lab_result_review"
    | "other"

export type AppointmentContactMethod = "phone" | "sms" | "app"

export interface Appointment {
    id: string
    patient_id: string
    doctor_id: string
    start_at: string
    end_at: string
    duration_minutes: number
    status: AppointmentStatus
    appointment_type: AppointmentType
    chief_complaint: string
    symptoms?: string | null
    notes?: string | null
    contact_phone?: string | null
    preferred_contact_method: AppointmentContactMethod
    is_follow_up: boolean
    doctor_response_note?: string | null
    rejection_reason?: string | null
    decided_at?: string | null
    created_at: string
    updated_at: string
    patient_name?: string
    doctor_name?: string
}

export interface AppointmentRequestInput {
    patient_id: string
    doctor_id?: string
    start_at: string
    duration_minutes?: number
    appointment_type: AppointmentType
    chief_complaint: string
    symptoms?: string
    notes?: string
    contact_phone?: string
    preferred_contact_method?: AppointmentContactMethod
    is_follow_up?: boolean
}

export interface AppointmentDecisionInput {
    doctor_id: string
    decision: "accepted" | "rejected"
    doctor_response_note?: string
    rejection_reason?: string
}

export interface AppointmentMutationResponse {
    status: string
    appointment: Appointment
    message: string
}

export interface PatientAppointmentsResponse {
    patient_id: string
    appointments: Appointment[]
}

export interface DoctorAppointmentsResponse {
    doctor_id: string
    appointments: Appointment[]
}

export interface AppointmentReminder {
    appointment_id: string
    start_at: string
    end_at: string
    doctor_id?: string
    doctor_name?: string
    appointment_type: AppointmentType
    is_follow_up: boolean
    chief_complaint: string
    hours_until: number
    is_today: boolean
}

export interface AppointmentRemindersResponse {
    patient_id: string
    within_hours: number
    reminders: AppointmentReminder[]
}
