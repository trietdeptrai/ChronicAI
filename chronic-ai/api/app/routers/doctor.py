"""
Doctor Router - Endpoints for doctor-specific functionality.
"""
from __future__ import annotations

import io
import json
import logging
import re
import textwrap
import zipfile
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.db.database import get_supabase
from app.models.schemas import (
    BloodType,
    GenderType,
    GlucoseTiming,
    LanguagePref,
    ProfileStatus,
    RecordType,
    TriagePriority,
    VitalSource,
)
from app.services.llm import generate_clinical_summary

router = APIRouter(prefix="/doctor", tags=["Doctor"])
logger = logging.getLogger(__name__)

PATIENT_REQUIRED_TEXT_FIELDS = {
    "full_name",
    "phone_primary",
    "address_ward",
    "address_district",
    "address_province",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
}

PATIENT_OPTIONAL_TEXT_FIELDS = {
    "national_id",
    "phone_secondary",
    "address_street",
    "primary_diagnosis",
}


class PatientTextExportFormat(str, Enum):
    json = "json"
    pdf = "pdf"


def _extract_signed_url(signed: object) -> Optional[str]:
    if isinstance(signed, dict):
        return (
            signed.get("signedURL")
            or signed.get("signed_url")
            or (signed.get("data") or {}).get("signedURL")
            or (signed.get("data") or {}).get("signed_url")
        )
    return None


def _extract_record_doctor_comment(record: dict) -> Optional[str]:
    comment = record.get("doctor_comment")
    if isinstance(comment, str):
        comment = comment.strip() or None
    elif comment is not None:
        comment = str(comment).strip() or None

    analysis = record.get("analysis_result")
    if not comment and isinstance(analysis, dict):
        value = analysis.get("doctor_comment")
        if isinstance(value, str):
            comment = value.strip() or None

    if isinstance(analysis, dict) and "doctor_comment" in analysis:
        cleaned = dict(analysis)
        cleaned.pop("doctor_comment", None)
        record["analysis_result"] = cleaned

    return comment


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: Optional[str], field_name: str) -> str:
    normalized = _normalize_optional_text(value)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} cannot be empty.",
        )
    return normalized


def _serialize_for_supabase(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _prepare_patient_payload(payload: dict, partial: bool) -> dict:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key in PATIENT_REQUIRED_TEXT_FIELDS:
            if value is None:
                if partial:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"{key} cannot be null.",
                    )
                continue
            cleaned[key] = _normalize_required_text(str(value), key)
            continue

        if key in PATIENT_OPTIONAL_TEXT_FIELDS:
            cleaned[key] = _normalize_optional_text(str(value)) if value is not None else None
            continue

        if key == "email":
            cleaned[key] = _normalize_optional_text(str(value)) if value is not None else None
            continue

        cleaned[key] = value

    return {key: _serialize_for_supabase(value) for key, value in cleaned.items()}


def _is_unique_violation(exc: Exception) -> bool:
    return "duplicate key value violates unique constraint" in str(exc).lower()


def _apply_patient_filters(query: object, status_value: Optional[str], priority: Optional[str], search: Optional[str]):
    if status_value:
        query = query.eq("profile_status", status_value)
    if priority:
        query = query.eq("triage_priority", priority)
    if search:
        query = query.ilike("full_name", f"%{search}%")
    return query


def _attach_signed_patient_photo_url(supabase: object, patient: dict) -> None:
    photo_path = patient.get("profile_photo_url")
    if not photo_path or str(photo_path).startswith("http"):
        return

    try:
        signed = supabase.storage.from_(settings.patient_photo_bucket).create_signed_url(
            photo_path,
            settings.patient_photo_signed_url_ttl_seconds,
        )
    except Exception:
        logger.exception("Failed to create signed URL for patient photo path=%s", photo_path)
        return

    signed_url = _extract_signed_url(signed)
    if signed_url:
        patient["profile_photo_url"] = signed_url


def _remove_storage_paths(supabase: object, paths: list[str]) -> int:
    unique_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not path or str(path).startswith("http"):
            continue
        normalized = str(path).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_paths.append(normalized)

    failed_count = 0
    for index in range(0, len(unique_paths), 100):
        batch = unique_paths[index:index + 100]
        try:
            supabase.storage.from_(settings.patient_photo_bucket).remove(batch)
        except Exception:
            logger.exception("Failed to remove storage paths batch size=%s", len(batch))
            failed_count += len(batch)
    return failed_count


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _as_export_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False, default=_json_default)
    except Exception:
        return str(value)


def _safe_filename_component(value: Optional[str], default: str) -> str:
    raw = (value or "").strip()
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    return candidate or default


def _safe_slug(value: Optional[str], default: str) -> str:
    raw = (value or "").strip().lower()
    candidate = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return candidate or default


def _build_patient_export_basename(patient: dict, patient_uuid: UUID) -> str:
    patient_slug = _safe_slug(patient.get("full_name"), "patient")
    return f"{patient_slug}-{patient_uuid}"


def _ensure_file_extension(filename: str, extension: str) -> str:
    ext = extension.strip()
    if not ext:
        return filename
    if not ext.startswith("."):
        ext = f".{ext}"
    return filename if filename.lower().endswith(ext.lower()) else f"{filename}{ext}"


def _fetch_patient_records_for_export(supabase: object, patient_uuid: UUID) -> list[dict]:
    def _run_query(include_doctor_comment: bool):
        select_cols = (
            "id, record_type, title, content_text, analysis_result, "
            "is_verified, created_at, updated_at, image_path"
        )
        if include_doctor_comment:
            select_cols += ", doctor_comment"
        return supabase.table("medical_records").select(select_cols).eq(
            "patient_id", str(patient_uuid)
        ).order(
            "created_at", desc=True
        ).execute()

    try:
        result = _run_query(include_doctor_comment=True)
        records = result.data or []
    except Exception:
        result = _run_query(include_doctor_comment=False)
        records = result.data or []
        for record in records:
            record["doctor_comment"] = None

    for record in records:
        record["doctor_comment"] = _extract_record_doctor_comment(record)

    return records


def _build_patient_export_payload(supabase: object, patient_uuid: UUID) -> dict[str, Any]:
    patient_result = supabase.table("patients").select("*").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    patient_data = patient_result.data if patient_result else None
    if not isinstance(patient_data, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    vitals_result = supabase.table("vital_signs").select("*").eq(
        "patient_id", str(patient_uuid)
    ).order("recorded_at", desc=True).execute()

    consultations_result = supabase.table("consultations").select(
        "id, chief_complaint, status, priority, started_at, summary"
    ).eq(
        "patient_id", str(patient_uuid)
    ).order("started_at", desc=True).execute()

    records = _fetch_patient_records_for_export(supabase, patient_uuid)
    for record in records:
        image_path = record.get("image_path")
        if isinstance(image_path, str):
            record["file_extension"] = Path(image_path).suffix.lower()
        else:
            record["file_extension"] = None

    return {
        "schema_version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "patient_id": str(patient_uuid),
        "patient": patient_data,
        "vitals": vitals_result.data or [],
        "consultations": consultations_result.data or [],
        "records": records,
    }


def _patient_payload_to_pdf_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "ChronicAI Patient Export",
        f"Exported at: {payload.get('exported_at', '')}",
        f"Patient ID: {payload.get('patient_id', '')}",
        "",
        "Patient Profile",
    ]

    patient = payload.get("patient") if isinstance(payload.get("patient"), dict) else {}
    if patient:
        for key in sorted(patient.keys()):
            lines.append(f"{key}: {_as_export_text(patient.get(key))}")
    else:
        lines.append("No patient profile data.")

    lines.append("")
    vitals = payload.get("vitals") if isinstance(payload.get("vitals"), list) else []
    lines.append(f"Vital Signs ({len(vitals)})")
    if not vitals:
        lines.append("No vital signs data.")
    for index, vital in enumerate(vitals, start=1):
        lines.append(f"Vital #{index}")
        if isinstance(vital, dict):
            for key in sorted(vital.keys()):
                lines.append(f"  {key}: {_as_export_text(vital.get(key))}")
        else:
            lines.append(f"  {_as_export_text(vital)}")

    lines.append("")
    consultations = payload.get("consultations") if isinstance(payload.get("consultations"), list) else []
    lines.append(f"Consultations ({len(consultations)})")
    if not consultations:
        lines.append("No consultations data.")
    for index, consultation in enumerate(consultations, start=1):
        lines.append(f"Consultation #{index}")
        if isinstance(consultation, dict):
            for key in sorted(consultation.keys()):
                lines.append(f"  {key}: {_as_export_text(consultation.get(key))}")
        else:
            lines.append(f"  {_as_export_text(consultation)}")

    lines.append("")
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    lines.append(f"Medical Records ({len(records)})")
    if not records:
        lines.append("No medical records data.")
    for index, record in enumerate(records, start=1):
        lines.append(f"Record #{index}")
        if isinstance(record, dict):
            for key in sorted(record.keys()):
                lines.append(f"  {key}: {_as_export_text(record.get(key))}")
        else:
            lines.append(f"  {_as_export_text(record)}")
        lines.append("")

    return lines


def _escape_pdf_text(value: str) -> str:
    # Type-1 font streams are single-byte, so keep non-Latin characters as \uXXXX escapes.
    clean = value.replace("\r", " ").replace("\n", " ")
    ascii_safe = clean.encode("unicode_escape").decode("ascii")
    escaped = ascii_safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped


def _render_text_pdf(lines: list[str]) -> bytes:
    normalized_lines: list[str] = []
    for line in lines:
        text = str(line or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
        wrapped = textwrap.wrap(
            text,
            width=96,
            break_long_words=True,
            break_on_hyphens=False,
        )
        if wrapped:
            normalized_lines.extend(wrapped)
        else:
            normalized_lines.append("")

    page_width = 612
    page_height = 792
    top = 742
    leading = 14
    bottom = 50
    lines_per_page = max(1, int((top - bottom) / leading))

    pages = [
        normalized_lines[index:index + lines_per_page]
        for index in range(0, len(normalized_lines), lines_per_page)
    ] or [[""]]

    content_ids: list[int] = []
    page_ids: list[int] = []
    next_id = 4
    for _ in pages:
        content_ids.append(next_id)
        next_id += 1
        page_ids.append(next_id)
        next_id += 1

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    kids_refs = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids_refs}] /Count {len(page_ids)} >>"
    ).encode("ascii")

    for index, page_lines in enumerate(pages):
        content_commands = [
            "BT",
            "/F1 11 Tf",
            f"50 {top} Td",
            f"{leading} TL",
        ]
        if page_lines:
            content_commands.append(f"({_escape_pdf_text(page_lines[0])}) Tj")
            for line in page_lines[1:]:
                content_commands.append(f"T* ({_escape_pdf_text(line)}) Tj")
        content_commands.append("ET")

        content_stream = "\n".join(content_commands).encode("latin-1", "replace")
        content_id = content_ids[index]
        page_id = page_ids[index]

        objects[content_id] = (
            b"<< /Length "
            + str(len(content_stream)).encode("ascii")
            + b" >>\nstream\n"
            + content_stream
            + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")

    document = bytearray()
    document.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * next_id

    for obj_id in range(1, next_id):
        offsets[obj_id] = len(document)
        document.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        document.extend(objects[obj_id])
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {next_id}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, next_id):
        document.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))

    document.extend(
        f"trailer\n<< /Size {next_id} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(document)


def _unique_zip_name(base_name: str, used_names: set[str]) -> str:
    candidate = base_name
    stem = Path(base_name).stem
    extension = Path(base_name).suffix
    counter = 1
    while candidate in used_names:
        candidate = f"{stem}_{counter}{extension}"
        counter += 1
    used_names.add(candidate)
    return candidate


class ClinicalSummaryRequest(BaseModel):
    """Request for clinical summary generation."""

    consultation_id: str
    patient_id: str


class ClinicalSummaryResponse(BaseModel):
    """Clinical summary response."""

    consultation_id: str
    patient_id: str
    summary: str


class VitalSignCreateRequest(BaseModel):
    """Request to create a new vital sign entry."""

    recorded_at: Optional[datetime] = None
    recorded_by: Optional[str] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    blood_glucose: Optional[float] = None
    blood_glucose_timing: Optional[GlucoseTiming] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[VitalSource] = None


class PatientCreateRequest(BaseModel):
    """Create payload for a patient profile (non-record data)."""

    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: GenderType
    national_id: Optional[str] = Field(None, max_length=20)
    phone_primary: str = Field(..., min_length=3, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_ward: str = Field(..., min_length=1, max_length=100)
    address_district: str = Field(..., min_length=1, max_length=100)
    address_province: str = Field(..., min_length=1, max_length=100)
    emergency_contact_name: str = Field(..., min_length=1, max_length=255)
    emergency_contact_phone: str = Field(..., min_length=3, max_length=20)
    emergency_contact_relationship: str = Field(..., min_length=1, max_length=50)
    blood_type: BloodType = BloodType.UNKNOWN
    primary_diagnosis: Optional[str] = Field(None, max_length=20)
    triage_priority: TriagePriority = TriagePriority.low
    profile_status: ProfileStatus = ProfileStatus.active
    preferred_language: LanguagePref = LanguagePref.vi
    assigned_doctor_id: Optional[UUID] = None


class PatientUpdateRequest(BaseModel):
    """Update payload for patient profile fields only."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    national_id: Optional[str] = Field(None, max_length=20)
    phone_primary: Optional[str] = Field(None, min_length=3, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address_street: Optional[str] = None
    address_ward: Optional[str] = Field(None, min_length=1, max_length=100)
    address_district: Optional[str] = Field(None, min_length=1, max_length=100)
    address_province: Optional[str] = Field(None, min_length=1, max_length=100)
    emergency_contact_name: Optional[str] = Field(None, min_length=1, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, min_length=3, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, min_length=1, max_length=50)
    blood_type: Optional[BloodType] = None
    primary_diagnosis: Optional[str] = Field(None, max_length=20)
    triage_priority: Optional[TriagePriority] = None
    profile_status: Optional[ProfileStatus] = None
    preferred_language: Optional[LanguagePref] = None
    assigned_doctor_id: Optional[UUID] = None


@router.post("/summary", response_model=ClinicalSummaryResponse)
async def create_clinical_summary(request: ClinicalSummaryRequest):
    """
    Generate a clinical summary for a consultation.

    Uses AI to analyze consultation messages and patient context
    to generate professional clinical notes in Vietnamese.
    """
    try:
        consultation_uuid = UUID(request.consultation_id)
        patient_uuid = UUID(request.patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    summary = await generate_clinical_summary(
        consultation_id=consultation_uuid,
        patient_id=patient_uuid,
    )

    # Optionally save summary to consultation record
    supabase = get_supabase()
    supabase.table("consultations").update({"summary": summary}).eq(
        "id", request.consultation_id
    ).execute()

    return ClinicalSummaryResponse(
        consultation_id=request.consultation_id,
        patient_id=request.patient_id,
        summary=summary,
    )


@router.get("/patients")
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List all patients for doctor dashboard.

    Args:
        page: Page number (1-indexed)
        page_size: Number of patients per page
        status: Filter by profile status (active, inactive)
        priority: Filter by triage priority (low, medium, high, urgent)
        search: Search by patient name
    """
    supabase = get_supabase()

    # Build query
    query = supabase.table("patients").select(
        "id, full_name, date_of_birth, gender, phone_primary, email, "
        "address_ward, address_district, address_province, "
        "emergency_contact_name, emergency_contact_phone, emergency_contact_relationship, "
        "chronic_conditions, primary_diagnosis, triage_priority, "
        "profile_status, last_checkup_date, next_appointment_date, "
        "profile_photo_url, "
        "assigned_doctor_id"
    )
    query = _apply_patient_filters(query, status, priority, search)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)
    query = query.order("updated_at", desc=True)

    result = query.execute()

    patients = result.data or []
    for patient in patients:
        _attach_signed_patient_photo_url(supabase, patient)

    # Get total count with the same filters as list query.
    count_query = supabase.table("patients").select("id", count="exact")
    count_query = _apply_patient_filters(count_query, status, priority, search)
    count_result = count_query.execute()

    total = count_result.count if hasattr(count_result, "count") and count_result.count is not None else len(patients)

    return {
        "patients": patients,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/patients", status_code=status.HTTP_201_CREATED)
async def create_patient(request: PatientCreateRequest):
    """
    Create a patient profile (general demographics/contact info).

    This endpoint intentionally does not touch medical record entities.
    A linked users row is created first so patients remain auth-compatible.
    """
    supabase = get_supabase()

    patient_payload = _prepare_patient_payload(request.model_dump(), partial=False)
    patient_payload["date_of_birth"] = _serialize_for_supabase(request.date_of_birth)

    user_payload = {
        "phone_number": patient_payload["phone_primary"],
        "email": patient_payload.get("email"),
        "role": "patient",
        "is_active": True,
    }

    created_user_id: Optional[str] = None

    try:
        user_result = supabase.table("users").insert(user_payload).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number or email already exists.",
            ) from exc
        logger.exception("Failed to create linked user for patient profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create linked user for patient profile.",
        ) from exc

    if not user_result or not user_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Linked user creation returned no data.",
        )

    created_user_id = str(user_result.data[0]["id"])
    patient_payload["user_id"] = created_user_id

    try:
        patient_result = supabase.table("patients").insert(patient_payload).execute()
    except Exception as exc:
        if created_user_id:
            try:
                supabase.table("users").delete().eq("id", created_user_id).execute()
            except Exception:
                logger.exception("Rollback failed after patient create error user_id=%s", created_user_id)

        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient creation failed due to a uniqueness conflict.",
            ) from exc

        logger.exception("Failed to create patient profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient profile.",
        ) from exc

    if not patient_result or not patient_result.data:
        if created_user_id:
            try:
                supabase.table("users").delete().eq("id", created_user_id).execute()
            except Exception:
                logger.exception("Rollback failed after empty patient insert user_id=%s", created_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patient creation returned no data.",
        )

    patient_data = patient_result.data[0]
    _attach_signed_patient_photo_url(supabase, patient_data)

    return {
        "status": "success",
        "patient": patient_data,
        "message": "Patient created successfully.",
    }


@router.get("/patients/{patient_id}")
async def get_patient_detail(patient_id: str):
    """
    Get detailed patient information.

    Includes:
    - Core patient info
    - Chronic conditions
    - Current medications
    - Recent vital signs
    - Recent consultations
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()

    # Get patient info
    patient = supabase.table("patients").select("*").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()

    if not patient or not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get recent vitals
    vitals = supabase.table("vital_signs").select("*").eq(
        "patient_id", str(patient_uuid)
    ).order("recorded_at", desc=True).limit(10).execute()

    # Get recent consultations
    consultations = supabase.table("consultations").select(
        "id, chief_complaint, status, priority, started_at, summary"
    ).eq(
        "patient_id", str(patient_uuid)
    ).order("started_at", desc=True).limit(5).execute()

    patient_data = patient.data
    if patient_data:
        _attach_signed_patient_photo_url(supabase, patient_data)

    return {
        "patient": patient_data,
        "recent_vitals": vitals.data or [],
        "recent_consultations": consultations.data or [],
    }


@router.patch("/patients/{patient_id}")
async def update_patient(patient_id: str, request: PatientUpdateRequest):
    """
    Update patient profile information only.

    This endpoint explicitly excludes medical record CRUD concerns.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    update_fields = request.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes requested.",
        )

    supabase = get_supabase()
    existing_result = supabase.table("patients").select("*").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    existing_patient = existing_result.data if existing_result else None
    if not isinstance(existing_patient, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_update_payload = _prepare_patient_payload(update_fields, partial=True)

    if not patient_update_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid patient fields to update.",
        )

    try:
        update_result = supabase.table("patients").update(patient_update_payload).eq(
            "id", str(patient_uuid)
        ).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient update failed due to a uniqueness conflict.",
            ) from exc
        logger.exception("Failed to update patient_id=%s", patient_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient profile.",
        ) from exc

    if not update_result or not update_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patient update returned no data.",
        )

    user_update_payload: dict[str, Any] = {}
    if "phone_primary" in patient_update_payload:
        user_update_payload["phone_number"] = patient_update_payload["phone_primary"]
    if "email" in patient_update_payload:
        user_update_payload["email"] = patient_update_payload["email"]

    if user_update_payload and existing_patient.get("user_id"):
        try:
            supabase.table("users").update(user_update_payload).eq(
                "id", str(existing_patient["user_id"])
            ).eq(
                "role", "patient"
            ).execute()
        except Exception as exc:
            rollback_payload = {
                field: existing_patient.get(field)
                for field in patient_update_payload.keys()
            }
            rollback_payload = {
                field: _serialize_for_supabase(value)
                for field, value in rollback_payload.items()
            }
            try:
                supabase.table("patients").update(rollback_payload).eq(
                    "id", str(patient_uuid)
                ).execute()
            except Exception:
                logger.exception(
                    "Rollback failed after linked user update error patient_id=%s",
                    patient_id,
                )

            if _is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number or email already exists on another user.",
                ) from exc

            logger.exception("Failed to sync linked user while updating patient_id=%s", patient_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync linked user information.",
            ) from exc

    patient_data = update_result.data[0]
    _attach_signed_patient_photo_url(supabase, patient_data)

    return {
        "status": "success",
        "patient": patient_data,
        "message": "Patient profile updated successfully.",
    }


@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str):
    """
    Delete a patient profile and clean up linked profile/media data.

    This operation intentionally targets patient-level information and related
    storage artifacts; medical-record CRUD endpoints remain separate.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    patient_result = supabase.table("patients").select(
        "id, user_id, profile_photo_url"
    ).eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    patient_data = patient_result.data if patient_result else None
    if not isinstance(patient_data, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    records_result = supabase.table("medical_records").select(
        "image_path"
    ).eq(
        "patient_id", str(patient_uuid)
    ).execute()

    paths_to_remove: list[str] = []
    profile_photo = patient_data.get("profile_photo_url")
    if isinstance(profile_photo, str):
        paths_to_remove.append(profile_photo)

    for record in records_result.data or []:
        image_path = record.get("image_path")
        if isinstance(image_path, str):
            paths_to_remove.append(image_path)

    failed_cleanup_count = _remove_storage_paths(supabase, paths_to_remove)

    delete_result = supabase.table("patients").delete().eq(
        "id", str(patient_uuid)
    ).execute()
    if not delete_result or not delete_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient profile.",
        )

    cleanup_warning: Optional[str] = None
    linked_user_id = patient_data.get("user_id")
    if linked_user_id:
        try:
            supabase.table("users").delete().eq(
                "id", str(linked_user_id)
            ).eq(
                "role", "patient"
            ).execute()
        except Exception:
            logger.exception("Failed to delete linked user_id=%s", linked_user_id)
            cleanup_warning = "Patient deleted but linked user cleanup failed."

    if failed_cleanup_count:
        storage_warning = f"Failed to remove {failed_cleanup_count} stored file(s)."
        cleanup_warning = f"{cleanup_warning} {storage_warning}".strip() if cleanup_warning else storage_warning

    response = {
        "status": "success",
        "patient_id": patient_id,
        "user_id": str(linked_user_id) if linked_user_id else None,
        "message": "Patient deleted successfully.",
    }
    if cleanup_warning:
        response["warning"] = cleanup_warning
    return response


@router.get("/patients/{patient_id}/vitals")
async def get_patient_vitals(
    patient_id: str,
    limit: int = Query(30, ge=1, le=200),
):
    """
    Get recent vital signs for a patient.

    Args:
        patient_id: Patient UUID
        limit: Maximum number of vitals to return
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()

    vitals = supabase.table("vital_signs").select("*").eq(
        "patient_id", str(patient_uuid)
    ).order("recorded_at", desc=True).limit(limit).execute()

    return {
        "patient_id": patient_id,
        "vitals": vitals.data or [],
    }


@router.post("/patients/{patient_id}/vitals")
async def create_patient_vital(
    patient_id: str,
    request: VitalSignCreateRequest,
):
    """
    Create a new vital sign entry for a patient.

    Validates that at least one measurement is provided.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    # Ensure at least one measurement is present
    measurements = [
        request.blood_pressure_systolic,
        request.blood_pressure_diastolic,
        request.heart_rate,
        request.blood_glucose,
        request.temperature,
        request.oxygen_saturation,
        request.weight_kg,
    ]
    if all(value is None for value in measurements):
        raise HTTPException(
            status_code=400,
            detail="At least one vital measurement is required",
        )

    supabase = get_supabase()

    data = request.model_dump(exclude_none=True)
    data["patient_id"] = str(patient_uuid)
    data.setdefault("source", VitalSource.self_reported.value)

    if isinstance(data.get("source"), VitalSource):
        data["source"] = data["source"].value
    if isinstance(data.get("blood_glucose_timing"), GlucoseTiming):
        data["blood_glucose_timing"] = data["blood_glucose_timing"].value

    if isinstance(data.get("recorded_at"), datetime):
        data["recorded_at"] = data["recorded_at"].isoformat()

    result = supabase.table("vital_signs").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to create vital sign entry",
        )

    return {
        "status": "success",
        "vital": result.data[0],
    }


@router.get("/patients/{patient_id}/records")
async def get_patient_records(
    patient_id: str,
    record_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get medical records for a patient.

    Args:
        patient_id: Patient UUID
        record_type: Optional filter by record type
        limit: Maximum number of records
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()

    def _run_records_query(include_doctor_comment: bool):
        select_cols = (
            "id, record_type, title, content_text, analysis_result, "
            "is_verified, created_at, updated_at, image_path"
        )
        if include_doctor_comment:
            select_cols += ", doctor_comment"

        query = supabase.table("medical_records").select(select_cols).eq("patient_id", str(patient_uuid))
        if record_type:
            valid_types = {record.value for record in RecordType}
            if record_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid record_type. Allowed: {', '.join(sorted(valid_types))}",
                )
            query = query.eq("record_type", record_type)
        query = query.order("created_at", desc=True).limit(limit)
        return query.execute()

    try:
        result = _run_records_query(include_doctor_comment=True)
        records = result.data or []
    except HTTPException:
        raise
    except Exception:
        # Backward compatibility for DBs without doctor_comment column.
        result = _run_records_query(include_doctor_comment=False)
        records = result.data or []
        for record in records:
            record["doctor_comment"] = None

    bucket = settings.patient_photo_bucket
    ttl = settings.patient_photo_signed_url_ttl_seconds
    for record in records:
        record["doctor_comment"] = _extract_record_doctor_comment(record)
        image_path = record.get("image_path")
        if image_path:
            try:
                signed = supabase.storage.from_(bucket).create_signed_url(image_path, ttl)
            except Exception:
                signed = None
            signed_url = _extract_signed_url(signed)
            if signed_url:
                ext = Path(image_path).suffix.lower()
                file_kind = "pdf" if ext == ".pdf" else "image"
                record["file_url"] = signed_url
                record["file_kind"] = file_kind
                if file_kind == "image":
                    record["image_url"] = signed_url
        record.pop("image_path", None)

    return {
        "patient_id": patient_id,
        "records": records,
    }


@router.get("/patients/{patient_id}/export")
async def export_patient_text(
    patient_id: str,
    export_format: PatientTextExportFormat = Query(
        default=PatientTextExportFormat.json,
        alias="format",
        description="Export format for patient textual data (json or pdf).",
    ),
):
    """
    Export patient textual data as JSON or PDF.

    Includes patient profile, vitals, consultations, and record metadata/text.
    Binary record files are exported through /patients/{patient_id}/export/files.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    payload = _build_patient_export_payload(supabase, patient_uuid)
    patient = payload.get("patient") if isinstance(payload.get("patient"), dict) else {}
    base_name = _build_patient_export_basename(patient, patient_uuid)

    if export_format == PatientTextExportFormat.json:
        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8")
        filename = f"{base_name}.json"
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    pdf_lines = _patient_payload_to_pdf_lines(payload)
    pdf_bytes = _render_text_pdf(pdf_lines)
    filename = f"{base_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/patients/{patient_id}/export/files")
async def export_patient_record_files(patient_id: str):
    """
    Export patient record files as a ZIP archive.

    Files are copied byte-for-byte from storage with original extensions.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    patient_result = supabase.table("patients").select("id, full_name").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    patient_data = patient_result.data if patient_result else None
    if not isinstance(patient_data, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    records_result = supabase.table("medical_records").select(
        "id, title, image_path, record_type, created_at"
    ).eq("patient_id", str(patient_uuid)).not_.is_(
        "image_path", "null"
    ).order("created_at", desc=False).execute()

    records = records_result.data or []
    if not records:
        raise HTTPException(status_code=404, detail="No file attachments found for this patient")

    zip_buffer = io.BytesIO()
    used_names: set[str] = set()
    exported_count = 0

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, record in enumerate(records, start=1):
            storage_path = record.get("image_path")
            if not isinstance(storage_path, str) or not storage_path.strip():
                continue

            try:
                file_bytes = supabase.storage.from_(settings.patient_photo_bucket).download(storage_path)
            except Exception:
                logger.exception(
                    "Failed to export record file patient_id=%s record_id=%s path=%s",
                    patient_id,
                    record.get("id"),
                    storage_path,
                )
                continue

            if not file_bytes:
                continue

            extension = Path(storage_path).suffix
            default_name = f"record_{index}"
            name_hint = _safe_filename_component(record.get("title"), default_name)
            entry_name = _ensure_file_extension(name_hint, extension)
            entry_name = _unique_zip_name(entry_name, used_names)

            archive.writestr(entry_name, file_bytes)
            exported_count += 1

        manifest = {
            "patient_id": str(patient_uuid),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "files_exported": exported_count,
            "records": [
                {
                    "record_id": str(record.get("id")),
                    "record_type": record.get("record_type"),
                    "title": record.get("title"),
                    "image_path": record.get("image_path"),
                    "created_at": record.get("created_at"),
                }
                for record in records
            ],
        }
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default),
        )

    if exported_count == 0:
        raise HTTPException(
            status_code=500,
            detail="No files could be exported. Check storage paths and bucket access.",
        )

    zip_bytes = zip_buffer.getvalue()
    patient_slug = _safe_slug(patient_data.get("full_name"), "patient")
    filename = f"{patient_slug}-{patient_uuid}-files.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stats")
async def get_dashboard_stats(doctor_id: Optional[str] = None):
    """
    Get statistics for doctor dashboard.

    Returns:
    - Total patients
    - Urgent cases
    - Today's appointments
    - Pending consultations
    """
    supabase = get_supabase()

    # Base query for patients
    patient_query = supabase.table("patients").select("id", count="exact")
    if doctor_id:
        patient_query = patient_query.eq("assigned_doctor_id", doctor_id)

    patients_result = patient_query.execute()
    total_patients = patients_result.count if hasattr(patients_result, "count") else 0

    # Urgent cases
    urgent_query = supabase.table("patients").select("id", count="exact").eq(
        "triage_priority", "urgent"
    )
    if doctor_id:
        urgent_query = urgent_query.eq("assigned_doctor_id", doctor_id)

    urgent_result = urgent_query.execute()
    urgent_cases = urgent_result.count if hasattr(urgent_result, "count") else 0

    # High priority
    high_query = supabase.table("patients").select("id", count="exact").eq(
        "triage_priority", "high"
    )
    if doctor_id:
        high_query = high_query.eq("assigned_doctor_id", doctor_id)

    high_result = high_query.execute()
    high_priority = high_result.count if hasattr(high_result, "count") else 0

    # Active consultations
    active_consults = supabase.table("consultations").select(
        "id", count="exact"
    ).in_(
        "status", ["triage", "urgent"]
    ).execute()

    pending_consultations = active_consults.count if hasattr(active_consults, "count") else 0

    return {
        "total_patients": total_patients,
        "urgent_cases": urgent_cases,
        "high_priority": high_priority,
        "pending_consultations": pending_consultations,
        "alerts": urgent_cases + high_priority,
    }
