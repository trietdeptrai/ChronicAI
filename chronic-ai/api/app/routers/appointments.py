"""
Appointment Router - Booking and follow-up workflow for patients/doctors.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from app.db.database import get_supabase
from app.models.schemas import AppointmentRequestCreate, AppointmentDecisionRequest

router = APIRouter(prefix="/appointments", tags=["Appointments"])
logger = logging.getLogger(__name__)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _overlaps(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    return start_a < end_b and start_b < end_a


def _index_name_by_id(rows: list[dict], id_key: str, name_key: str = "full_name") -> dict[str, str]:
    names: dict[str, str] = {}
    for row in rows:
        row_id = row.get(id_key)
        row_name = row.get(name_key)
        if isinstance(row_id, str) and isinstance(row_name, str):
            names[row_id] = row_name
    return names


def _attach_related_names(
    supabase: object,
    appointments: list[dict],
    include_patient: bool,
    include_doctor: bool,
) -> list[dict]:
    if not appointments:
        return appointments

    if include_patient:
        patient_ids = sorted({row.get("patient_id") for row in appointments if row.get("patient_id")})
        if patient_ids:
            patient_result = supabase.table("patients").select(
                "id, full_name"
            ).in_(
                "id", patient_ids
            ).execute()
            patient_names = _index_name_by_id(patient_result.data or [], "id")
            for row in appointments:
                patient_id = row.get("patient_id")
                if patient_id in patient_names:
                    row["patient_name"] = patient_names[patient_id]

    if include_doctor:
        doctor_ids = sorted({row.get("doctor_id") for row in appointments if row.get("doctor_id")})
        if doctor_ids:
            doctor_result = supabase.table("doctors").select(
                "id, full_name"
            ).in_(
                "id", doctor_ids
            ).execute()
            doctor_names = _index_name_by_id(doctor_result.data or [], "id")
            for row in appointments:
                doctor_id = row.get("doctor_id")
                if doctor_id in doctor_names:
                    row["doctor_name"] = doctor_names[doctor_id]

    return appointments


def _validate_appointment_window(start_at: datetime, duration_minutes: int) -> tuple[datetime, datetime]:
    start_utc = _ensure_utc(start_at)
    end_utc = start_utc + timedelta(minutes=duration_minutes)
    now_utc = datetime.now(timezone.utc)
    if start_utc <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Appointment time must be in the future.",
        )
    return start_utc, end_utc


def _find_conflicting_appointment(
    supabase: object,
    doctor_id: UUID,
    start_at: datetime,
    end_at: datetime,
    *,
    exclude_id: Optional[UUID] = None,
) -> Optional[dict]:
    # Fetch a narrow window around the target slot to reduce payload.
    window_start = (start_at - timedelta(hours=12)).isoformat()
    window_end = (end_at + timedelta(hours=12)).isoformat()
    query = supabase.table("appointments").select(
        "id, start_at, end_at, status"
    ).eq(
        "doctor_id", str(doctor_id)
    ).eq(
        "status", "accepted"
    ).gte(
        "end_at", window_start
    ).lte(
        "start_at", window_end
    )
    if exclude_id:
        query = query.neq("id", str(exclude_id))

    result = query.execute()
    for candidate in result.data or []:
        candidate_start = _parse_timestamp(candidate.get("start_at"))
        candidate_end = _parse_timestamp(candidate.get("end_at"))
        if not candidate_start or not candidate_end:
            continue
        if _overlaps(start_at, end_at, candidate_start, candidate_end):
            return candidate
    return None


def _refresh_patient_next_appointment(supabase: object, patient_id: UUID) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    next_result = supabase.table("appointments").select(
        "start_at"
    ).eq(
        "patient_id", str(patient_id)
    ).eq(
        "status", "accepted"
    ).gte(
        "start_at", now_iso
    ).order(
        "start_at", desc=False
    ).limit(1).execute()

    next_appointment = None
    if next_result.data:
        next_appointment = next_result.data[0].get("start_at")

    supabase.table("patients").update(
        {"next_appointment_date": next_appointment}
    ).eq(
        "id", str(patient_id)
    ).execute()




@router.post("/request", status_code=status.HTTP_201_CREATED)
async def request_appointment(payload: AppointmentRequestCreate):
    """
    Patient requests an appointment slot. Default status is `pending`.
    """
    supabase = get_supabase()
    start_at, end_at = _validate_appointment_window(payload.start_at, payload.duration_minutes)

    patient_result = supabase.table("patients").select(
        "id, full_name, assigned_doctor_id, phone_primary"
    ).eq(
        "id", str(payload.patient_id)
    ).maybe_single().execute()
    patient = patient_result.data if patient_result else None
    if not isinstance(patient, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    doctor_id = payload.doctor_id or patient.get("assigned_doctor_id")
    if not doctor_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Doctor must be provided or assigned to patient.",
        )
    doctor_uuid = UUID(str(doctor_id))

    doctor_result = supabase.table("doctors").select(
        "id, full_name"
    ).eq(
        "id", str(doctor_uuid)
    ).maybe_single().execute()
    doctor = doctor_result.data if doctor_result else None
    if not isinstance(doctor, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

    conflict = _find_conflicting_appointment(supabase, doctor_uuid, start_at, end_at)
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected slot conflicts with an existing accepted appointment.",
        )

    is_follow_up = payload.is_follow_up
    if is_follow_up is None:
        is_follow_up = payload.appointment_type == "follow_up"

    insert_payload = {
        "patient_id": str(payload.patient_id),
        "doctor_id": str(doctor_uuid),
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "duration_minutes": payload.duration_minutes,
        "status": "pending",
        "appointment_type": payload.appointment_type,
        "chief_complaint": payload.chief_complaint.strip(),
        "symptoms": payload.symptoms.strip() if isinstance(payload.symptoms, str) else None,
        "notes": payload.notes.strip() if isinstance(payload.notes, str) else None,
        "contact_phone": payload.contact_phone or patient.get("phone_primary"),
        "preferred_contact_method": payload.preferred_contact_method,
        "is_follow_up": is_follow_up,
    }
    created = supabase.table("appointments").insert(insert_payload).execute()
    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create appointment request.",
        )

    appointment = created.data[0]
    appointment["patient_name"] = patient.get("full_name")
    appointment["doctor_name"] = doctor.get("full_name")
    return {
        "status": "success",
        "appointment": appointment,
        "message": "Appointment request submitted successfully.",
    }


@router.get("/patient/{patient_id}")
async def list_patient_appointments(
    patient_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    status_filter: Optional[Literal["pending", "accepted", "rejected", "cancelled", "completed"]] = Query(
        None,
        alias="status",
    ),
):
    try:
        patient_uuid = UUID(patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid patient_id format") from exc

    supabase = get_supabase()
    query = supabase.table("appointments").select("*").eq("patient_id", str(patient_uuid))
    if start:
        query = query.gte("start_at", _ensure_utc(start).isoformat())
    if end:
        query = query.lte("start_at", _ensure_utc(end).isoformat())
    if status_filter:
        query = query.eq("status", status_filter)

    result = query.order("start_at", desc=False).execute()
    appointments = _attach_related_names(
        supabase,
        result.data or [],
        include_patient=False,
        include_doctor=True,
    )
    return {
        "patient_id": patient_id,
        "appointments": appointments,
    }


@router.get("/doctor/{doctor_id}")
async def list_doctor_appointments(
    doctor_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    status_filter: Optional[Literal["pending", "accepted", "rejected", "cancelled", "completed"]] = Query(
        None,
        alias="status",
    ),
):
    try:
        doctor_uuid = UUID(doctor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid doctor_id format") from exc

    supabase = get_supabase()
    query = supabase.table("appointments").select("*").eq("doctor_id", str(doctor_uuid))
    if start:
        query = query.gte("start_at", _ensure_utc(start).isoformat())
    if end:
        query = query.lte("start_at", _ensure_utc(end).isoformat())
    if status_filter:
        query = query.eq("status", status_filter)

    result = query.order("start_at", desc=False).execute()
    appointments = _attach_related_names(
        supabase,
        result.data or [],
        include_patient=True,
        include_doctor=False,
    )
    return {
        "doctor_id": doctor_id,
        "appointments": appointments,
    }


@router.patch("/{appointment_id}/decision")
async def decide_appointment(appointment_id: str, payload: AppointmentDecisionRequest):
    """
    Doctor accepts or rejects a pending appointment request.
    """
    try:
        appointment_uuid = UUID(appointment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid appointment_id format") from exc

    supabase = get_supabase()
    current_result = supabase.table("appointments").select(
        "*"
    ).eq(
        "id", str(appointment_uuid)
    ).maybe_single().execute()
    current = current_result.data if current_result else None
    if not isinstance(current, dict):
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if str(current.get("doctor_id")) != str(payload.doctor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor is not assigned to this appointment.",
        )

    current_status = current.get("status")
    if current_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only pending appointments can be decided. Current status: {current_status}",
        )

    start_at = _parse_timestamp(current.get("start_at"))
    end_at = _parse_timestamp(current.get("end_at"))
    if not start_at or not end_at:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored appointment window is invalid.",
        )

    if payload.decision == "accepted":
        conflict = _find_conflicting_appointment(
            supabase,
            payload.doctor_id,
            start_at,
            end_at,
            exclude_id=appointment_uuid,
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot accept appointment due to schedule conflict.",
            )

    if payload.decision == "rejected" and not (
        (payload.rejection_reason and payload.rejection_reason.strip())
        or (payload.doctor_response_note and payload.doctor_response_note.strip())
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rejection requires rejection_reason or doctor_response_note.",
        )

    update_payload = {
        "status": payload.decision,
        "doctor_response_note": payload.doctor_response_note.strip()
        if isinstance(payload.doctor_response_note, str)
        else None,
        "rejection_reason": payload.rejection_reason.strip()
        if isinstance(payload.rejection_reason, str)
        else None,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    updated_result = supabase.table("appointments").update(update_payload).eq(
        "id", str(appointment_uuid)
    ).execute()
    if not updated_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update appointment decision.",
        )

    patient_id = current.get("patient_id")
    if patient_id:
        try:
            _refresh_patient_next_appointment(supabase, UUID(str(patient_id)))
        except Exception:
            logger.exception("Failed to refresh next appointment for patient_id=%s", patient_id)

    appointment = updated_result.data[0]
    appointment = _attach_related_names(
        supabase,
        [appointment],
        include_patient=True,
        include_doctor=True,
    )[0]
    return {
        "status": "success",
        "appointment": appointment,
        "message": f"Appointment {payload.decision}.",
    }


@router.get("/patient/{patient_id}/reminders")
async def get_patient_appointment_reminders(
    patient_id: str,
    within_hours: int = Query(48, ge=1, le=24 * 14),
):
    """
    Return upcoming accepted appointments for in-app reminder popups.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid patient_id format") from exc

    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    until = now + timedelta(hours=within_hours)
    result = supabase.table("appointments").select(
        "*"
    ).eq(
        "patient_id", str(patient_uuid)
    ).eq(
        "status", "accepted"
    ).gte(
        "start_at", now.isoformat()
    ).lte(
        "start_at", until.isoformat()
    ).order(
        "start_at", desc=False
    ).execute()

    appointments = _attach_related_names(
        supabase,
        result.data or [],
        include_patient=False,
        include_doctor=True,
    )
    reminders: list[dict] = []
    for appointment in appointments:
        start_at = _parse_timestamp(appointment.get("start_at"))
        if not start_at:
            continue
        hours_until = (start_at - now).total_seconds() / 3600
        reminders.append({
            "appointment_id": appointment.get("id"),
            "start_at": appointment.get("start_at"),
            "end_at": appointment.get("end_at"),
            "doctor_id": appointment.get("doctor_id"),
            "doctor_name": appointment.get("doctor_name"),
            "appointment_type": appointment.get("appointment_type"),
            "is_follow_up": bool(appointment.get("is_follow_up")),
            "chief_complaint": appointment.get("chief_complaint"),
            "hours_until": round(hours_until, 1),
            "is_today": start_at.date() == now.date(),
        })

    return {
        "patient_id": patient_id,
        "within_hours": within_hours,
        "reminders": reminders,
    }
