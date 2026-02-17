/**
 * Doctor patient list page with patient profile CRUD.
 */
"use client"

import Link from "next/link"
import { useMemo, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ArrowRight, Search, Settings, UserPlus, X } from "lucide-react"

import { useAuth } from "@/contexts"
import {
    useCreatePatient,
    useDebounce,
    useDeletePatientProfile,
    usePatients,
    useUpdatePatient,
} from "@/lib/hooks"
import type { Patient, PatientCreateInput, PatientUpdateInput } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/alert-dialog"

const priorityFilters = ["", "urgent", "high", "medium", "low"] as const
const genderOptions = ["female", "male", "other"] as const
const triageOptions = ["low", "medium", "high", "urgent"] as const
const statusOptions = ["active", "inactive", "deceased", "suspended"] as const

type PatientFormState = {
    full_name: string
    date_of_birth: string
    gender: "male" | "female" | "other"
    phone_primary: string
    email: string
    address_ward: string
    address_district: string
    address_province: string
    emergency_contact_name: string
    emergency_contact_phone: string
    emergency_contact_relationship: string
    triage_priority: "low" | "medium" | "high" | "urgent"
    profile_status: "active" | "inactive" | "deceased" | "suspended"
}

const EMPTY_FORM: PatientFormState = {
    full_name: "",
    date_of_birth: "",
    gender: "female",
    phone_primary: "",
    email: "",
    address_ward: "",
    address_district: "",
    address_province: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relationship: "",
    triage_priority: "low",
    profile_status: "active",
}

export default function PatientsPage() {
    const router = useRouter()
    const { role } = useAuth()
    const [search, setSearch] = useState("")
    const [priority, setPriority] = useState("")
    const [createOpen, setCreateOpen] = useState(false)
    const [editPatient, setEditPatient] = useState<Patient | null>(null)
    const [deletePatient, setDeletePatient] = useState<Patient | null>(null)
    const [form, setForm] = useState<PatientFormState>(EMPTY_FORM)
    const [formError, setFormError] = useState<string | null>(null)
    const debouncedSearch = useDebounce(search, 300)

    const listQuery = usePatients({
        page: 1,
        pageSize: 100,
        search: debouncedSearch || undefined,
        priority: priority || undefined,
    })
    const createMutation = useCreatePatient()
    const updateMutation = useUpdatePatient()
    const deleteMutation = useDeletePatientProfile()

    const patients = listQuery.data?.patients ?? []
    const pageLabel = useMemo(() => {
        if (!listQuery.data) return ""
        return `Page ${listQuery.data.page}/${Math.max(listQuery.data.total_pages, 1)} - ${listQuery.data.total} patients`
    }, [listQuery.data])

    if (role !== "doctor") {
        return (
            <Card>
                <CardContent className="p-6 text-sm text-muted-foreground">
                    This page is available for doctor accounts only.
                </CardContent>
            </Card>
        )
    }

    const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending

    const openCreate = () => {
        setForm(EMPTY_FORM)
        setFormError(null)
        setCreateOpen(true)
    }

    const openEdit = (patient: Patient) => {
        setForm({
            full_name: patient.full_name ?? "",
            date_of_birth: patient.date_of_birth ?? "",
            gender: patient.gender ?? "female",
            phone_primary: patient.phone_primary ?? "",
            email: patient.email ?? "",
            address_ward: patient.address_ward ?? "",
            address_district: patient.address_district ?? "",
            address_province: patient.address_province ?? "",
            emergency_contact_name: patient.emergency_contact_name ?? "",
            emergency_contact_phone: patient.emergency_contact_phone ?? "",
            emergency_contact_relationship: patient.emergency_contact_relationship ?? "",
            triage_priority: patient.triage_priority ?? "low",
            profile_status: patient.profile_status ?? "active",
        })
        setFormError(null)
        setEditPatient(patient)
    }

    const validateForm = (): string | null => {
        const required = [
            form.full_name,
            form.date_of_birth,
            form.phone_primary,
            form.address_ward,
            form.address_district,
            form.address_province,
            form.emergency_contact_name,
            form.emergency_contact_phone,
            form.emergency_contact_relationship,
        ]
        return required.some((value) => !value.trim()) ? "Please fill all required fields." : null
    }

    const buildCreatePayload = (): PatientCreateInput => ({
        full_name: form.full_name.trim(),
        date_of_birth: form.date_of_birth,
        gender: form.gender,
        phone_primary: form.phone_primary.trim(),
        email: normalizeOptional(form.email) || undefined,
        address_ward: form.address_ward.trim(),
        address_district: form.address_district.trim(),
        address_province: form.address_province.trim(),
        emergency_contact_name: form.emergency_contact_name.trim(),
        emergency_contact_phone: form.emergency_contact_phone.trim(),
        emergency_contact_relationship: form.emergency_contact_relationship.trim(),
        triage_priority: form.triage_priority,
        profile_status: form.profile_status,
    })

    const buildUpdatePayload = (): PatientUpdateInput => ({
        full_name: form.full_name.trim(),
        date_of_birth: form.date_of_birth,
        gender: form.gender,
        phone_primary: form.phone_primary.trim(),
        email: normalizeOptional(form.email),
        address_ward: form.address_ward.trim(),
        address_district: form.address_district.trim(),
        address_province: form.address_province.trim(),
        emergency_contact_name: form.emergency_contact_name.trim(),
        emergency_contact_phone: form.emergency_contact_phone.trim(),
        emergency_contact_relationship: form.emergency_contact_relationship.trim(),
        triage_priority: form.triage_priority,
        profile_status: form.profile_status,
    })

    const submitCreate = () => {
        const err = validateForm()
        if (err) {
            setFormError(err)
            return
        }
        createMutation.mutate(buildCreatePayload(), {
            onSuccess: (result) => {
                setCreateOpen(false)
                setForm(EMPTY_FORM)
                setFormError(null)
                toast.success(result.message || "Patient created successfully.")
            },
            onError: (error) => setFormError(getErrorMessage(error, "Failed to create patient.")),
        })
    }

    const submitUpdate = () => {
        if (!editPatient) return
        const err = validateForm()
        if (err) {
            setFormError(err)
            return
        }
        updateMutation.mutate(
            { patientId: editPatient.id, data: buildUpdatePayload() },
            {
                onSuccess: (result) => {
                    setEditPatient(null)
                    setForm(EMPTY_FORM)
                    setFormError(null)
                    toast.success(result.message || "Patient updated successfully.")
                },
                onError: (error) => setFormError(getErrorMessage(error, "Failed to update patient.")),
            }
        )
    }

    const submitDelete = () => {
        if (!deletePatient) return
        deleteMutation.mutate(
            { patientId: deletePatient.id },
            {
                onSuccess: (result) => {
                    toast.success(result.warning ? `${result.message} ${result.warning}` : result.message)
                    setDeletePatient(null)
                },
                onError: (error) => toast.error(getErrorMessage(error, "Failed to delete patient.")),
            }
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div className="space-y-1">
                    <h1 className="text-2xl font-bold text-[#1e2939]">Patients</h1>
                    <p className="text-sm text-[#4a5565]">Manage patient profile information separately from medical files.</p>
                </div>
                <Button onClick={openCreate}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    New Patient
                </Button>
            </div>

            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by patient name" className="pl-9" />
                    </div>
                    <div className="w-full md:w-64">
                        <select value={priority} onChange={(e) => setPriority(e.target.value)} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs md:text-sm">
                            {priorityFilters.map((option) => (
                                <option key={option} value={option}>
                                    {option || "All priorities"}
                                </option>
                            ))}
                        </select>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3">
                    {pageLabel && <p className="text-xs text-muted-foreground">{pageLabel}</p>}
                    {listQuery.isLoading && <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Loading patients...</div>}
                    {listQuery.error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">Failed to load patients.</div>}
                    {!listQuery.isLoading && !listQuery.error && patients.length === 0 && <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">No matching patients.</div>}
                    {!listQuery.isLoading && !listQuery.error && patients.length > 0 && (
                        <div className="grid gap-3 md:grid-cols-2">
                            {patients.map((patient) => (
                                <div key={patient.id} className="rounded-xl border bg-background p-4 transition hover:border-primary/40 hover:shadow-sm">
                                    <button type="button" onClick={() => router.push(`/dashboard/patients/${patient.id}`)} className="w-full text-left">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="font-semibold text-foreground">{patient.full_name}</p>
                                                <p className="mt-1 text-xs text-muted-foreground">{patient.gender} - {patient.phone_primary}</p>
                                            </div>
                                            {patient.triage_priority && <Badge variant="outline">{patient.triage_priority}</Badge>}
                                        </div>
                                        <p className="mt-2 text-xs text-muted-foreground">Last checkup: {formatDate(patient.last_checkup_date)}</p>
                                    </button>
                                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                                        <Button size="sm" variant="outline" asChild>
                                            <Link href={`/dashboard/patients/${patient.id}`}>Detail <ArrowRight className="ml-1 h-4 w-4" /></Link>
                                        </Button>
                                        <Button size="sm" variant="outline" onClick={() => openEdit(patient)}><Settings className="mr-1 h-3.5 w-3.5" />Edit</Button>
                                        <Button size="sm" variant="destructive" onClick={() => setDeletePatient(patient)}><X className="mr-1 h-3.5 w-3.5" />Delete</Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) { setForm(EMPTY_FORM); setFormError(null) } }}>
                <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
                    <DialogHeader><DialogTitle>Create Patient</DialogTitle></DialogHeader>
                    <PatientForm form={form} setForm={setForm} />
                    {formError && <p className="text-sm text-destructive">{formError}</p>}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
                        <Button onClick={submitCreate} disabled={isPending}>{createMutation.isPending ? "Creating..." : "Create"}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!editPatient} onOpenChange={(open) => { if (!open) { setEditPatient(null); setFormError(null) } }}>
                <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
                    <DialogHeader><DialogTitle>Update Patient</DialogTitle></DialogHeader>
                    <PatientForm form={form} setForm={setForm} />
                    {formError && <p className="text-sm text-destructive">{formError}</p>}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditPatient(null)}>Cancel</Button>
                        <Button onClick={submitUpdate} disabled={isPending || !editPatient}>{updateMutation.isPending ? "Saving..." : "Save"}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!deletePatient} onOpenChange={(open) => { if (!open) setDeletePatient(null) }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete patient profile?</AlertDialogTitle>
                        <AlertDialogDescription>This action removes patient profile information and linked records.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={submitDelete} disabled={isPending}>{deleteMutation.isPending ? "Deleting..." : "Delete"}</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}

function PatientForm({ form, setForm }: { form: PatientFormState; setForm: (value: PatientFormState) => void }) {
    const setValue = <K extends keyof PatientFormState>(field: K, value: PatientFormState[K]) => setForm({ ...form, [field]: value })
    return (
        <div className="grid gap-3 md:grid-cols-2">
            <Field label="Full Name *"><Input value={form.full_name} onChange={(e) => setValue("full_name", e.target.value)} /></Field>
            <Field label="Date of Birth *"><Input type="date" value={form.date_of_birth} onChange={(e) => setValue("date_of_birth", e.target.value)} /></Field>
            <Field label="Gender *"><select value={form.gender} onChange={(e) => setValue("gender", e.target.value as PatientFormState["gender"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">{genderOptions.map((v) => <option key={v} value={v}>{v}</option>)}</select></Field>
            <Field label="Primary Phone *"><Input value={form.phone_primary} onChange={(e) => setValue("phone_primary", e.target.value)} /></Field>
            <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setValue("email", e.target.value)} /></Field>
            <Field label="Ward *"><Input value={form.address_ward} onChange={(e) => setValue("address_ward", e.target.value)} /></Field>
            <Field label="District *"><Input value={form.address_district} onChange={(e) => setValue("address_district", e.target.value)} /></Field>
            <Field label="Province *"><Input value={form.address_province} onChange={(e) => setValue("address_province", e.target.value)} /></Field>
            <Field label="Emergency Contact Name *"><Input value={form.emergency_contact_name} onChange={(e) => setValue("emergency_contact_name", e.target.value)} /></Field>
            <Field label="Emergency Contact Phone *"><Input value={form.emergency_contact_phone} onChange={(e) => setValue("emergency_contact_phone", e.target.value)} /></Field>
            <Field label="Emergency Relationship *"><Input value={form.emergency_contact_relationship} onChange={(e) => setValue("emergency_contact_relationship", e.target.value)} /></Field>
            <Field label="Triage Priority"><select value={form.triage_priority} onChange={(e) => setValue("triage_priority", e.target.value as PatientFormState["triage_priority"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">{triageOptions.map((v) => <option key={v} value={v}>{v}</option>)}</select></Field>
            <Field label="Profile Status"><select value={form.profile_status} onChange={(e) => setValue("profile_status", e.target.value as PatientFormState["profile_status"])} className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm">{statusOptions.map((v) => <option key={v} value={v}>{v}</option>)}</select></Field>
        </div>
    )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
    return <div className="grid gap-2"><Label>{label}</Label>{children}</div>
}

function normalizeOptional(value: string): string | null {
    const normalized = value.trim()
    return normalized ? normalized : null
}

function formatDate(value?: string): string {
    if (!value) return "--"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString()
}

function getErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object" && "message" in error) {
        const message = String((error as { message?: unknown }).message || "").trim()
        if (message) return message
    }
    return fallback
}
