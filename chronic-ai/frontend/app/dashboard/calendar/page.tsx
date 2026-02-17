"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { PageHeader } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useAuth, useDashboardLanguage, type DashboardLanguage } from "@/contexts"
import {
  useDecideAppointment,
  useDoctorAppointments,
  usePatient,
  usePatientAppointmentReminders,
  usePatientAppointments,
  useRequestAppointment,
} from "@/lib/hooks"
import type { Appointment, AppointmentReminder, AppointmentStatus, AppointmentType } from "@/types"

type ViewMode = "day" | "week"
type ContactMethod = "phone" | "sms" | "app"
type DecisionType = "accepted" | "rejected"

interface BookingFormState {
  appointmentType: AppointmentType
  chiefComplaint: string
  symptoms: string
  notes: string
  contactPhone: string
  contactMethod: ContactMethod
  durationMinutes: number
  isFollowUp: boolean
}

interface EventLayout {
  appointment: Appointment
  startMin: number
  endMin: number
  top: number
  height: number
  column: number
  columnCount: number
}

const GRID_START_HOUR = 7
const GRID_END_HOUR = 20
const SLOT_MINUTES = 30
const ROW_HEIGHT = 36
const DAY_START_MIN = GRID_START_HOUR * 60
const DAY_END_MIN = GRID_END_HOUR * 60

const DEFAULT_FORM: BookingFormState = {
  appointmentType: "follow_up",
  chiefComplaint: "",
  symptoms: "",
  notes: "",
  contactPhone: "",
  contactMethod: "phone",
  durationMinutes: 30,
  isFollowUp: true,
}

const COPY = {
  vi: {
    title: "Lich hen",
    desc: "Giao dien lich kieu Google Calendar.",
    today: "Hom nay",
    day: "Ngay",
    week: "Tuan",
    month: "Thang",
    range: "Khoang thoi gian",
    loading: "Dang tai...",
    noRole: "Khong xac dinh vai tro.",
    noAppointments: "Khong co lich hen.",
    type: "Loai",
    reason: "Ly do",
    symptoms: "Trieu chung",
    notes: "Ghi chu",
    phone: "So dien thoai",
    contact: "Kenh lien he",
    duration: "Thoi luong",
    followUp: "Tai kham dinh ky",
    bookingTitle: "Dat lich",
    bookingDesc: "Dien thong tin dat lich.",
    bookingSubmit: "Xac nhan",
    cancel: "Huy",
    chooseDateTime: "Ngay gio",
    decisionNote: "Ghi chu bac si",
    rejectionReason: "Ly do tu choi",
    accept: "Chap nhan",
    reject: "Tu choi",
    decisionSubmit: "Xac nhan",
    decisionAcceptTitle: "Xac nhan lich",
    decisionRejectTitle: "Tu choi lich",
    reminderTitle: "Nhac lich",
    reminderDesc: "Ban co lich hen sap toi.",
    dismiss: "Da hieu",
    requiredReason: "Nhap ly do kham.",
    bookedOk: "Da gui yeu cau dat lich.",
    acceptOk: "Da xac nhan lich.",
    rejectOk: "Da tu choi lich.",
    patient: "Benh nhan",
    doctor: "Bac si",
    status: {
      pending: "Cho xac nhan",
      accepted: "Da xac nhan",
      rejected: "Da tu choi",
      cancelled: "Da huy",
      completed: "Da hoan thanh",
    },
    types: {
      follow_up: "Tai kham",
      routine_check: "Kham dinh ky",
      new_symptom: "Trieu chung moi",
      medication_review: "Ra soat thuoc",
      lab_result_review: "Xem ket qua xet nghiem",
      other: "Khac",
    },
    contactMethods: {
      phone: "Goi dien",
      sms: "SMS",
      app: "Thong bao app",
    },
  },
  en: {
    title: "Appointments",
    desc: "Google Calendar-style scheduling.",
    today: "Today",
    day: "Day",
    week: "Week",
    month: "Month",
    range: "Range",
    loading: "Loading...",
    noRole: "Role not available.",
    noAppointments: "No appointments.",
    type: "Type",
    reason: "Reason",
    symptoms: "Symptoms",
    notes: "Notes",
    phone: "Phone",
    contact: "Contact",
    duration: "Duration",
    followUp: "Regular follow-up",
    bookingTitle: "Book appointment",
    bookingDesc: "Fill booking details.",
    bookingSubmit: "Confirm",
    cancel: "Cancel",
    chooseDateTime: "Date time",
    decisionNote: "Doctor note",
    rejectionReason: "Rejection reason",
    accept: "Accept",
    reject: "Reject",
    decisionSubmit: "Submit",
    decisionAcceptTitle: "Accept appointment",
    decisionRejectTitle: "Reject appointment",
    reminderTitle: "Reminder",
    reminderDesc: "You have an upcoming appointment.",
    dismiss: "Dismiss",
    requiredReason: "Please enter reason.",
    bookedOk: "Booking request sent.",
    acceptOk: "Appointment accepted.",
    rejectOk: "Appointment rejected.",
    patient: "Patient",
    doctor: "Doctor",
    status: {
      pending: "Pending",
      accepted: "Accepted",
      rejected: "Rejected",
      cancelled: "Cancelled",
      completed: "Completed",
    },
    types: {
      follow_up: "Follow-up",
      routine_check: "Routine check",
      new_symptom: "New symptom",
      medication_review: "Medication review",
      lab_result_review: "Lab review",
      other: "Other",
    },
    contactMethods: {
      phone: "Phone",
      sms: "SMS",
      app: "In-app",
    },
  },
} as const

export default function CalendarPage() {
  const { role, user } = useAuth()
  const { language } = useDashboardLanguage()
  const t = COPY[language]

  const isPatient = role === "patient"
  const isDoctor = role === "doctor"
  const patientId = isPatient ? user?.id ?? "" : ""
  const doctorId = isDoctor ? user?.id ?? "" : ""

  const [viewMode, setViewMode] = useState<ViewMode>("week")
  const [selectedDate, setSelectedDate] = useState(() => new Date())
  const [miniMonth, setMiniMonth] = useState(() => new Date())

  const [bookingOpen, setBookingOpen] = useState(false)
  const [decisionOpen, setDecisionOpen] = useState(false)
  const [bookingDateTime, setBookingDateTime] = useState<Date | null>(null)
  const [bookingForm, setBookingForm] = useState<BookingFormState>(DEFAULT_FORM)
  const [decisionTarget, setDecisionTarget] = useState<Appointment | null>(null)
  const [decisionType, setDecisionType] = useState<DecisionType>("accepted")
  const [decisionNote, setDecisionNote] = useState("")
  const [rejectionReason, setRejectionReason] = useState("")
  const [focusedAppointment, setFocusedAppointment] = useState<Appointment | null>(null)

  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reminderOpen, setReminderOpen] = useState(false)
  const [activeReminder, setActiveReminder] = useState<AppointmentReminder | null>(null)

  const visibleRange = useMemo(() => {
    if (viewMode === "day") {
      return {
        start: startOfDayLocal(selectedDate),
        end: endOfDayLocal(selectedDate),
      }
    }
    const start = startOfWeekMonday(selectedDate)
    return {
      start,
      end: endOfDayLocal(addDays(start, 6)),
    }
  }, [selectedDate, viewMode])

  const patientAppointments = usePatientAppointments(
    patientId,
    {
      start: visibleRange.start.toISOString(),
      end: visibleRange.end.toISOString(),
    },
    isPatient && !!patientId
  )

  const doctorAppointments = useDoctorAppointments(
    doctorId,
    {
      start: visibleRange.start.toISOString(),
      end: visibleRange.end.toISOString(),
    },
    isDoctor && !!doctorId
  )

  const reminders = usePatientAppointmentReminders(patientId, 48, isPatient && !!patientId)
  const patientProfile = usePatient(patientId)
  const requestAppointment = useRequestAppointment()
  const decideAppointment = useDecideAppointment()

  const appointments = useMemo(() => {
    if (isDoctor) return doctorAppointments.data?.appointments ?? []
    if (isPatient) return patientAppointments.data?.appointments ?? []
    return []
  }, [doctorAppointments.data?.appointments, isDoctor, isPatient, patientAppointments.data?.appointments])

  const currentDays = useMemo(() => {
    if (viewMode === "day") return [startOfDayLocal(selectedDate)]
    const first = startOfWeekMonday(selectedDate)
    return Array.from({ length: 7 }, (_, index) => addDays(first, index))
  }, [selectedDate, viewMode])

  const appointmentsByDay = useMemo(() => {
    const map = new Map<string, Appointment[]>()
    for (const day of currentDays) map.set(dayKey(day), [])
    for (const appointment of appointments) {
      const key = dayKey(new Date(appointment.start_at))
      const list = map.get(key)
      if (list) list.push(appointment)
    }
    for (const [, list] of map) {
      list.sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    }
    return map
  }, [appointments, currentDays])

  const markedDays = useMemo(() => appointments.map((item) => new Date(item.start_at)), [appointments])

  const rangeAppointments = useMemo(() => {
    const output: Appointment[] = []
    for (const day of currentDays) {
      const list = appointmentsByDay.get(dayKey(day))
      if (list) output.push(...list)
    }
    return output
  }, [appointmentsByDay, currentDays])

  useEffect(() => {
    if (!isPatient || activeReminder || !(reminders.data?.reminders?.length)) return
    const firstVisible = reminders.data.reminders.find((reminder) => {
      if (typeof window === "undefined") return true
      return sessionStorage.getItem(buildReminderDismissKey(reminder)) !== "1"
    })
    if (!firstVisible) return
    const timer = window.setTimeout(() => {
      setActiveReminder(firstVisible)
      setReminderOpen(true)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [activeReminder, isPatient, reminders.data?.reminders])

  function navigate(direction: "prev" | "next") {
    const step = viewMode === "day" ? 1 : 7
    const nextDate = addDays(selectedDate, direction === "prev" ? -step : step)
    setSelectedDate(nextDate)
    setMiniMonth(nextDate)
  }

  function jumpToToday() {
    const now = new Date()
    setSelectedDate(now)
    setMiniMonth(now)
  }

  function selectDate(date: Date) {
    setSelectedDate(date)
    setMiniMonth(date)
  }

  function openBooking(slotDateTime: Date) {
    if (!isPatient) return
    setBookingDateTime(slotDateTime)
    setBookingForm((prev) => ({
      ...prev,
      contactPhone: patientProfile.data?.patient?.phone_primary ?? prev.contactPhone,
    }))
    setMessage(null)
    setError(null)
    setBookingOpen(true)
  }

  async function submitBooking() {
    if (!bookingDateTime || !patientId) return
    if (!bookingForm.chiefComplaint.trim()) {
      setError(t.requiredReason)
      return
    }

    try {
      await requestAppointment.mutateAsync({
        patient_id: patientId,
        doctor_id: patientProfile.data?.patient?.assigned_doctor_id || undefined,
        start_at: bookingDateTime.toISOString(),
        duration_minutes: bookingForm.durationMinutes,
        appointment_type: bookingForm.appointmentType,
        chief_complaint: bookingForm.chiefComplaint.trim(),
        symptoms: bookingForm.symptoms.trim() || undefined,
        notes: bookingForm.notes.trim() || undefined,
        contact_phone: bookingForm.contactPhone.trim() || undefined,
        preferred_contact_method: bookingForm.contactMethod,
        is_follow_up: bookingForm.isFollowUp,
      })
      setBookingOpen(false)
      setMessage(t.bookedOk)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed")
    }
  }

  function openDecision(target: Appointment, type: DecisionType) {
    setDecisionTarget(target)
    setDecisionType(type)
    setDecisionNote(target.doctor_response_note ?? "")
    setRejectionReason(target.rejection_reason ?? "")
    setDecisionOpen(true)
    setMessage(null)
    setError(null)
  }

  async function submitDecision() {
    if (!decisionTarget || !doctorId) return
    if (decisionType === "rejected" && !rejectionReason.trim() && !decisionNote.trim()) {
      setError(t.rejectionReason)
      return
    }
    try {
      await decideAppointment.mutateAsync({
        appointmentId: decisionTarget.id,
        payload: {
          doctor_id: doctorId,
          decision: decisionType,
          doctor_response_note: decisionNote.trim() || undefined,
          rejection_reason: rejectionReason.trim() || undefined,
        },
      })
      setDecisionOpen(false)
      setMessage(decisionType === "accepted" ? t.acceptOk : t.rejectOk)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed")
    }
  }

  function dismissReminder() {
    if (activeReminder && typeof window !== "undefined") {
      sessionStorage.setItem(buildReminderDismissKey(activeReminder), "1")
    }
    setReminderOpen(false)
    setActiveReminder(null)
  }

  if (!role) {
    return (
      <div className="space-y-6">
        <PageHeader title={t.title} description={t.desc} />
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">{t.noRole}</CardContent>
        </Card>
      </div>
    )
  }

  const isLoading = isDoctor ? doctorAppointments.isLoading : patientAppointments.isLoading

  return (
    <div className="space-y-6">
      <PageHeader title={t.title} description={t.desc} />

      {message && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="p-4 text-sm text-emerald-700">{message}</CardContent>
        </Card>
      )}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}

      <Card className="bg-white/80">
        <CardContent className="p-4 md:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={jumpToToday}>{t.today}</Button>
              <Button variant="outline" size="icon" onClick={() => navigate("prev")}><ChevronLeft className="h-4 w-4" /></Button>
              <Button variant="outline" size="icon" onClick={() => navigate("next")}><ChevronRight className="h-4 w-4" /></Button>
              <span className="ml-2 text-sm font-semibold text-foreground">
                {formatRangeLabel(visibleRange.start, visibleRange.end, viewMode, language)}
              </span>
            </div>

            <div className="inline-flex rounded-md border bg-background p-1">
              <button
                type="button"
                onClick={() => setViewMode("day")}
                className={`rounded px-3 py-1.5 text-sm font-medium ${viewMode === "day" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
              >
                {t.day}
              </button>
              <button
                type="button"
                onClick={() => setViewMode("week")}
                className={`rounded px-3 py-1.5 text-sm font-medium ${viewMode === "week" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
              >
                {t.week}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[300px_1fr]">
        <Card className="bg-white/80">
          <CardHeader>
            <CardTitle>{t.month}</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={(date) => date && selectDate(date)}
              month={miniMonth}
              onMonthChange={setMiniMonth}
              showOutsideDays
              fixedWeeks
              weekStartsOn={1}
              className="w-[290px]"
              modifiers={{ hasAppointment: markedDays }}
              modifiersClassNames={{ hasAppointment: "bg-primary/10 text-primary font-semibold" }}
            />
          </CardContent>
        </Card>

        <Card className="bg-white/80">
          <CardHeader>
            <CardTitle>{t.range}</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading && <p className="text-sm text-muted-foreground">{t.loading}</p>}

            {!isLoading && viewMode === "day" && (
              <DayGrid
                date={currentDays[0]}
                appointments={appointmentsByDay.get(dayKey(currentDays[0])) ?? []}
                language={language}
                isPatient={isPatient}
                focusedAppointmentId={focusedAppointment?.id}
                onSlotClick={openBooking}
                onEventClick={setFocusedAppointment}
              />
            )}

            {!isLoading && viewMode === "week" && (
              <WeekGrid
                days={currentDays}
                appointmentsByDay={appointmentsByDay}
                selectedDate={selectedDate}
                language={language}
                isPatient={isPatient}
                focusedAppointmentId={focusedAppointment?.id}
                onSelectDate={selectDate}
                onSlotClick={openBooking}
                onEventClick={setFocusedAppointment}
              />
            )}

            {!isLoading && rangeAppointments.length === 0 && (
              <p className="mt-4 text-sm text-muted-foreground">{t.noAppointments}</p>
            )}

            {focusedAppointment && (
              <div className="mt-4 rounded-lg border bg-background p-4 text-sm">
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant={statusBadgeVariant(focusedAppointment.status)}>{t.status[focusedAppointment.status]}</Badge>
                  <span className="font-medium">{formatDateTime(focusedAppointment.start_at, language)}</span>
                </div>
                <p><span className="font-medium">{t.type}: </span>{t.types[focusedAppointment.appointment_type]}</p>
                <p><span className="font-medium">{t.reason}: </span>{focusedAppointment.chief_complaint}</p>
                {focusedAppointment.patient_name && <p><span className="font-medium">{t.patient}: </span>{focusedAppointment.patient_name}</p>}
                {focusedAppointment.doctor_name && <p><span className="font-medium">{t.doctor}: </span>{focusedAppointment.doctor_name}</p>}
                {isDoctor && focusedAppointment.status === "pending" && (
                  <div className="mt-3 flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => openDecision(focusedAppointment, "accepted")}>{t.accept}</Button>
                    <Button size="sm" variant="destructive" onClick={() => openDecision(focusedAppointment, "rejected")}>{t.reject}</Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={bookingOpen} onOpenChange={setBookingOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{t.bookingTitle}</DialogTitle>
            <DialogDescription>{t.bookingDesc}</DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="grid gap-2">
              <Label>{t.chooseDateTime}</Label>
              <Input value={bookingDateTime ? formatDateTime(bookingDateTime.toISOString(), language) : "--"} readOnly />
            </div>
            <div className="grid gap-2">
              <Label>{t.type}</Label>
              <select
                className="h-9 rounded-md border bg-input-background px-3 text-sm"
                value={bookingForm.appointmentType}
                onChange={(event) => setBookingForm((prev) => ({ ...prev, appointmentType: event.target.value as AppointmentType }))}
              >
                {(Object.keys(COPY.vi.types) as AppointmentType[]).map((type) => (
                  <option key={type} value={type}>{t.types[type]}</option>
                ))}
              </select>
            </div>
            <div className="grid gap-2">
              <Label>{t.reason}</Label>
              <Textarea value={bookingForm.chiefComplaint} onChange={(event) => setBookingForm((prev) => ({ ...prev, chiefComplaint: event.target.value }))} />
            </div>
            <div className="grid gap-2">
              <Label>{t.symptoms}</Label>
              <Textarea value={bookingForm.symptoms} onChange={(event) => setBookingForm((prev) => ({ ...prev, symptoms: event.target.value }))} />
            </div>
            <div className="grid gap-2">
              <Label>{t.notes}</Label>
              <Textarea value={bookingForm.notes} onChange={(event) => setBookingForm((prev) => ({ ...prev, notes: event.target.value }))} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>{t.phone}</Label>
                <Input value={bookingForm.contactPhone} onChange={(event) => setBookingForm((prev) => ({ ...prev, contactPhone: event.target.value }))} />
              </div>
              <div className="grid gap-2">
                <Label>{t.contact}</Label>
                <select
                  className="h-9 rounded-md border bg-input-background px-3 text-sm"
                  value={bookingForm.contactMethod}
                  onChange={(event) => setBookingForm((prev) => ({ ...prev, contactMethod: event.target.value as ContactMethod }))}
                >
                  <option value="phone">{t.contactMethods.phone}</option>
                  <option value="sms">{t.contactMethods.sms}</option>
                  <option value="app">{t.contactMethods.app}</option>
                </select>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>{t.duration}</Label>
                <select
                  className="h-9 rounded-md border bg-input-background px-3 text-sm"
                  value={bookingForm.durationMinutes}
                  onChange={(event) => setBookingForm((prev) => ({ ...prev, durationMinutes: Number(event.target.value) }))}
                >
                  <option value={30}>30 min</option>
                  <option value={45}>45 min</option>
                  <option value={60}>60 min</option>
                </select>
              </div>
              <label className="flex items-center gap-2 pt-7 text-sm">
                <input type="checkbox" checked={bookingForm.isFollowUp} onChange={(event) => setBookingForm((prev) => ({ ...prev, isFollowUp: event.target.checked }))} />
                <span>{t.followUp}</span>
              </label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setBookingOpen(false)}>{t.cancel}</Button>
            <Button onClick={submitBooking} disabled={requestAppointment.isPending}>{t.bookingSubmit}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={decisionOpen} onOpenChange={setDecisionOpen}>
        <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{decisionType === "accepted" ? t.decisionAcceptTitle : t.decisionRejectTitle}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-2">
              <Label>{t.decisionNote}</Label>
              <Textarea value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} />
            </div>
            {decisionType === "rejected" && (
              <div className="grid gap-2">
                <Label>{t.rejectionReason}</Label>
                <Textarea value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDecisionOpen(false)}>{t.cancel}</Button>
            <Button
              variant={decisionType === "accepted" ? "default" : "destructive"}
              onClick={submitDecision}
              disabled={decideAppointment.isPending}
            >
              {t.decisionSubmit}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={reminderOpen} onOpenChange={setReminderOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.reminderTitle}</DialogTitle>
            <DialogDescription>{t.reminderDesc}</DialogDescription>
          </DialogHeader>
          {activeReminder && (
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">{t.doctor}: </span>{activeReminder.doctor_name ?? "--"}</p>
              <p><span className="font-medium">{t.reason}: </span>{activeReminder.chief_complaint}</p>
              <p><span className="font-medium">{t.chooseDateTime}: </span>{formatDateTime(activeReminder.start_at, language)}</p>
            </div>
          )}
          <DialogFooter>
            <Button onClick={dismissReminder}>{t.dismiss}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function DayGrid({
  date,
  appointments,
  language,
  isPatient,
  focusedAppointmentId,
  onSlotClick,
  onEventClick,
}: {
  date: Date
  appointments: Appointment[]
  language: DashboardLanguage
  isPatient: boolean
  focusedAppointmentId?: string
  onSlotClick: (slotDateTime: Date) => void
  onEventClick: (appointment: Appointment) => void
}) {
  const rows = useMemo(() => buildTimeRows(DAY_START_MIN, DAY_END_MIN), [])
  const layouts = useMemo(() => buildEventLayouts(appointments), [appointments])
  const nowLine = getNowLineOffset(date)

  return (
    <div className="rounded-xl border bg-white">
      <div className="grid grid-cols-[74px_1fr] border-b bg-slate-50/80">
        <div />
        <div className="px-4 py-2 text-sm font-semibold text-foreground">
          {formatDayHeader(date, language)}
        </div>
      </div>

      <div className="grid h-[780px] grid-cols-[74px_1fr] overflow-auto">
        <div className="border-r bg-white">
          {rows.map((minute, index) => (
            <div
              key={`label-${minute}`}
              className={`border-t px-2 pt-1 text-[11px] text-muted-foreground ${index === 0 ? "border-t-0" : ""}`}
              style={{ height: ROW_HEIGHT }}
            >
              {minute % 60 === 0 ? `${pad2(Math.floor(minute / 60))}:00` : ""}
            </div>
          ))}
        </div>

        <div className="relative">
          {rows.map((minute, index) => {
            const slotDate = withMinuteOfDay(date, minute)
            return (
              <button
                key={`slot-${minute}`}
                type="button"
                onClick={() => isPatient && onSlotClick(slotDate)}
                className={`w-full border-t px-2 text-left ${isPatient ? "cursor-pointer hover:bg-sky-50" : "cursor-default"} ${index === 0 ? "border-t-0" : ""}`}
                style={{ height: ROW_HEIGHT }}
                aria-label={`Slot ${formatTime(slotDate, language)}`}
              >
                <span className="text-[10px] text-transparent">{isPatient ? "slot" : ""}</span>
              </button>
            )
          })}

          {nowLine !== null && (
            <div className="pointer-events-none absolute left-0 right-0 z-10 h-[2px] bg-red-500/80" style={{ top: nowLine }} />
          )}

          <div className="pointer-events-none absolute inset-0">
            {layouts.map((layout) => {
              const isFocused = focusedAppointmentId === layout.appointment.id
              return (
                <button
                  key={layout.appointment.id}
                  type="button"
                  onClick={() => onEventClick(layout.appointment)}
                  className={`pointer-events-auto absolute rounded-md border px-2 py-1 text-left text-[11px] shadow-sm ${statusBlockClass(layout.appointment.status)} ${isFocused ? "ring-2 ring-primary" : ""}`}
                  style={{
                    top: layout.top,
                    height: layout.height,
                    left: `calc(${(layout.column / layout.columnCount) * 100}% + 3px)`,
                    width: `calc(${100 / layout.columnCount}% - 6px)`,
                  }}
                >
                  <p className="truncate font-semibold">
                    {formatTime(layout.appointment.start_at, language)} - {formatTime(layout.appointment.end_at, language)}
                  </p>
                  <p className="truncate">{layout.appointment.chief_complaint}</p>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function WeekGrid({
  days,
  appointmentsByDay,
  selectedDate,
  language,
  isPatient,
  focusedAppointmentId,
  onSelectDate,
  onSlotClick,
  onEventClick,
}: {
  days: Date[]
  appointmentsByDay: Map<string, Appointment[]>
  selectedDate: Date
  language: DashboardLanguage
  isPatient: boolean
  focusedAppointmentId?: string
  onSelectDate: (date: Date) => void
  onSlotClick: (slotDateTime: Date) => void
  onEventClick: (appointment: Appointment) => void
}) {
  const rows = useMemo(() => buildTimeRows(DAY_START_MIN, DAY_END_MIN), [])

  return (
    <div className="overflow-x-auto rounded-xl border bg-white">
      <div className="min-w-[980px]">
        <div className="grid grid-cols-[74px_repeat(7,minmax(0,1fr))] border-b bg-slate-50/80">
          <div />
          {days.map((day) => {
            const selected = isSameDayLocal(day, selectedDate)
            return (
              <button
                key={`week-head-${dayKey(day)}`}
                type="button"
                onClick={() => onSelectDate(day)}
                className={`border-l px-2 py-2 text-left ${selected ? "bg-primary/10" : ""}`}
              >
                <p className="text-xs text-muted-foreground">{formatWeekday(day, language)}</p>
                <p className="text-sm font-semibold text-foreground">{formatDateShort(day, language)}</p>
              </button>
            )
          })}
        </div>

        <div className="h-[780px] overflow-auto">
          <div className="grid grid-cols-[74px_repeat(7,minmax(0,1fr))]">
            <div className="border-r bg-white">
              {rows.map((minute, index) => (
                <div
                  key={`week-label-${minute}`}
                  className={`border-t px-2 pt-1 text-[11px] text-muted-foreground ${index === 0 ? "border-t-0" : ""}`}
                  style={{ height: ROW_HEIGHT }}
                >
                  {minute % 60 === 0 ? `${pad2(Math.floor(minute / 60))}:00` : ""}
                </div>
              ))}
            </div>

            {days.map((day) => {
              const events = appointmentsByDay.get(dayKey(day)) ?? []
              const layouts = buildEventLayouts(events)
              const nowLine = getNowLineOffset(day)

              return (
                <div key={`week-col-${dayKey(day)}`} className="relative border-l">
                  {rows.map((minute, index) => {
                    const slotDate = withMinuteOfDay(day, minute)
                    return (
                      <button
                        key={`week-slot-${dayKey(day)}-${minute}`}
                        type="button"
                        onClick={() => isPatient && onSlotClick(slotDate)}
                        className={`w-full border-t px-1 text-left ${isPatient ? "cursor-pointer hover:bg-sky-50" : "cursor-default"} ${index === 0 ? "border-t-0" : ""}`}
                        style={{ height: ROW_HEIGHT }}
                        aria-label={`Slot ${formatTime(slotDate, language)}`}
                      >
                        <span className="text-[10px] text-transparent">{isPatient ? "slot" : ""}</span>
                      </button>
                    )
                  })}

                  {nowLine !== null && (
                    <div className="pointer-events-none absolute left-0 right-0 z-10 h-[2px] bg-red-500/80" style={{ top: nowLine }} />
                  )}

                  <div className="pointer-events-none absolute inset-0">
                    {layouts.map((layout) => {
                      const isFocused = focusedAppointmentId === layout.appointment.id
                      return (
                        <button
                          key={layout.appointment.id}
                          type="button"
                          onClick={() => onEventClick(layout.appointment)}
                          className={`pointer-events-auto absolute rounded-md border px-2 py-1 text-left text-[11px] shadow-sm ${statusBlockClass(layout.appointment.status)} ${isFocused ? "ring-2 ring-primary" : ""}`}
                          style={{
                            top: layout.top,
                            height: layout.height,
                            left: `calc(${(layout.column / layout.columnCount) * 100}% + 3px)`,
                            width: `calc(${100 / layout.columnCount}% - 6px)`,
                          }}
                        >
                          <p className="truncate font-semibold">{formatTime(layout.appointment.start_at, language)}</p>
                          <p className="truncate">{layout.appointment.chief_complaint}</p>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function buildTimeRows(startMin: number, endMin: number): number[] {
  const rows: number[] = []
  for (let minute = startMin; minute < endMin; minute += SLOT_MINUTES) rows.push(minute)
  return rows
}

function buildEventLayouts(appointments: Appointment[]): EventLayout[] {
  const events = appointments
    .map((appointment) => {
      const start = new Date(appointment.start_at)
      const end = new Date(appointment.end_at)
      const startMin = Math.max(getMinuteOfDay(start), DAY_START_MIN)
      const endMin = Math.min(getMinuteOfDay(end), DAY_END_MIN)
      if (endMin <= startMin) return null
      return { appointment, startMin, endMin }
    })
    .filter((value): value is { appointment: Appointment; startMin: number; endMin: number } => !!value)
    .sort((a, b) => (a.startMin - b.startMin) || (a.endMin - b.endMin))

  if (events.length === 0) return []

  const output: EventLayout[] = []
  let cluster: Array<{ appointment: Appointment; startMin: number; endMin: number }> = []
  let clusterEnd = -1

  const flushCluster = () => {
    if (cluster.length === 0) return

    const active: Array<{ endMin: number; column: number }> = []
    const assigned = cluster.map((item) => ({ ...item, column: 0 }))
    let maxColumns = 1

    for (const item of assigned) {
      for (let i = active.length - 1; i >= 0; i -= 1) {
        if (active[i].endMin <= item.startMin) active.splice(i, 1)
      }
      const used = new Set(active.map((entry) => entry.column))
      let column = 0
      while (used.has(column)) column += 1
      item.column = column
      active.push({ endMin: item.endMin, column })
      if (active.length > maxColumns) maxColumns = active.length
    }

    for (const item of assigned) {
      output.push({
        appointment: item.appointment,
        startMin: item.startMin,
        endMin: item.endMin,
        top: ((item.startMin - DAY_START_MIN) / SLOT_MINUTES) * ROW_HEIGHT,
        height: Math.max(((item.endMin - item.startMin) / SLOT_MINUTES) * ROW_HEIGHT - 2, 20),
        column: item.column,
        columnCount: maxColumns,
      })
    }

    cluster = []
    clusterEnd = -1
  }

  for (const event of events) {
    if (cluster.length === 0) {
      cluster.push(event)
      clusterEnd = event.endMin
      continue
    }
    if (event.startMin < clusterEnd) {
      cluster.push(event)
      clusterEnd = Math.max(clusterEnd, event.endMin)
      continue
    }
    flushCluster()
    cluster.push(event)
    clusterEnd = event.endMin
  }

  flushCluster()
  return output
}

function getNowLineOffset(day: Date): number | null {
  const now = new Date()
  if (!isSameDayLocal(now, day)) return null
  const minute = getMinuteOfDay(now)
  if (minute < DAY_START_MIN || minute > DAY_END_MIN) return null
  return ((minute - DAY_START_MIN) / SLOT_MINUTES) * ROW_HEIGHT
}

function statusBlockClass(status: AppointmentStatus): string {
  if (status === "accepted") return "border-sky-300 bg-sky-100 text-sky-900"
  if (status === "pending") return "border-amber-300 bg-amber-100 text-amber-900"
  if (status === "rejected") return "border-red-300 bg-red-100 text-red-900"
  if (status === "completed") return "border-emerald-300 bg-emerald-100 text-emerald-900"
  return "border-slate-300 bg-slate-100 text-slate-800"
}

function statusBadgeVariant(status: AppointmentStatus): "default" | "secondary" | "destructive" | "outline" {
  if (status === "accepted") return "default"
  if (status === "pending") return "secondary"
  if (status === "rejected") return "destructive"
  return "outline"
}

function startOfDayLocal(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

function endOfDayLocal(date: Date): Date {
  const d = new Date(date)
  d.setHours(23, 59, 59, 999)
  return d
}

function startOfWeekMonday(date: Date): Date {
  const d = startOfDayLocal(date)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  return addDays(d, diff)
}

function addDays(date: Date, amount: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + amount)
  return d
}

function withMinuteOfDay(date: Date, minuteOfDay: number): Date {
  const d = new Date(date)
  d.setHours(Math.floor(minuteOfDay / 60), minuteOfDay % 60, 0, 0)
  return d
}

function getMinuteOfDay(date: Date): number {
  return date.getHours() * 60 + date.getMinutes()
}

function isSameDayLocal(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function formatRangeLabel(start: Date, end: Date, viewMode: ViewMode, language: DashboardLanguage): string {
  const locale = language === "vi" ? "vi-VN" : "en-US"
  if (viewMode === "day") {
    return start.toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "long", year: "numeric" })
  }
  const startText = start.toLocaleDateString(locale, { day: "2-digit", month: "short" })
  const endText = end.toLocaleDateString(locale, { day: "2-digit", month: "short", year: "numeric" })
  return `${startText} - ${endText}`
}

function formatDayHeader(date: Date, language: DashboardLanguage): string {
  return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function formatWeekday(date: Date, language: DashboardLanguage): string {
  return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { weekday: "short" })
}

function formatDateShort(date: Date, language: DashboardLanguage): string {
  return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { day: "2-digit", month: "2-digit" })
}

function formatDateTime(value: string, language: DashboardLanguage): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(language === "vi" ? "vi-VN" : "en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatTime(value: string | Date, language: DashboardLanguage): string {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return "--:--"
  return date.toLocaleTimeString(language === "vi" ? "vi-VN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

function pad2(value: number): string {
  return String(value).padStart(2, "0")
}

function buildReminderDismissKey(reminder: AppointmentReminder): string {
  return `appointment-reminder:${reminder.appointment_id}:${reminder.start_at}`
}
