"""
Doctor Router - Endpoints for doctor-specific functionality.
"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from app.db.database import get_supabase
from app.config import settings
from app.models.schemas import RecordType, VitalSource, GlucoseTiming
from app.services.llm import generate_clinical_summary


router = APIRouter(prefix="/doctor", tags=["Doctor"])


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
        patient_id=patient_uuid
    )
    
    # Optionally save summary to consultation record
    supabase = get_supabase()
    supabase.table("consultations").update({
        "summary": summary
    }).eq("id", request.consultation_id).execute()
    
    return ClinicalSummaryResponse(
        consultation_id=request.consultation_id,
        patient_id=request.patient_id,
        summary=summary
    )


@router.get("/patients")
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
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
        "id, full_name, date_of_birth, gender, phone_primary, "
        "chronic_conditions, primary_diagnosis, triage_priority, "
        "profile_status, last_checkup_date, next_appointment_date, "
        "profile_photo_url, "
        "assigned_doctor_id"
    )
    
    if status:
        query = query.eq("profile_status", status)
    
    if priority:
        query = query.eq("triage_priority", priority)
    
    if search:
        query = query.ilike("full_name", f"%{search}%")
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)
    query = query.order("updated_at", desc=True)
    
    result = query.execute()
    
    patients = result.data or []
    bucket = settings.patient_photo_bucket
    ttl = settings.patient_photo_signed_url_ttl_seconds
    for patient in patients:
        photo_path = patient.get("profile_photo_url")
        if photo_path and not str(photo_path).startswith("http"):
            signed = supabase.storage.from_(bucket).create_signed_url(photo_path, ttl)
            signed_url = None
            if isinstance(signed, dict):
                signed_url = (
                    signed.get("signedURL")
                    or signed.get("signed_url")
                    or (signed.get("data") or {}).get("signedURL")
                    or (signed.get("data") or {}).get("signed_url")
                )
            if signed_url:
                patient["profile_photo_url"] = signed_url
    
    # Get total count
    count_result = supabase.table("patients").select(
        "id", count="exact"
    ).execute()
    
    total = count_result.count if hasattr(count_result, 'count') else len(result.data)
    
    return {
        "patients": patients,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
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
    ).single().execute()
    
    if not patient.data:
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
        photo_path = patient_data.get("profile_photo_url")
        if photo_path and not str(photo_path).startswith("http"):
            signed = supabase.storage.from_(settings.patient_photo_bucket).create_signed_url(
                photo_path,
                settings.patient_photo_signed_url_ttl_seconds
            )
            signed_url = None
            if isinstance(signed, dict):
                signed_url = (
                    signed.get("signedURL")
                    or signed.get("signed_url")
                    or (signed.get("data") or {}).get("signedURL")
                    or (signed.get("data") or {}).get("signed_url")
                )
            if signed_url:
                patient_data["profile_photo_url"] = signed_url
    
    return {
        "patient": patient_data,
        "recent_vitals": vitals.data or [],
        "recent_consultations": consultations.data or []
    }


@router.get("/patients/{patient_id}/vitals")
async def get_patient_vitals(
    patient_id: str,
    limit: int = Query(30, ge=1, le=200)
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
        "vitals": vitals.data or []
    }


@router.post("/patients/{patient_id}/vitals")
async def create_patient_vital(
    patient_id: str,
    request: VitalSignCreateRequest
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
        request.weight_kg
    ]
    if all(value is None for value in measurements):
        raise HTTPException(
            status_code=400,
            detail="At least one vital measurement is required"
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
            detail="Failed to create vital sign entry"
        )
    
    return {
        "status": "success",
        "vital": result.data[0]
    }


@router.get("/patients/{patient_id}/records")
async def get_patient_records(
    patient_id: str,
    record_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
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
    
    query = supabase.table("medical_records").select(
        "id, record_type, title, content_text, analysis_result, "
        "is_verified, created_at, image_path"
    ).eq("patient_id", str(patient_uuid))
    
    if record_type:
        valid_types = {record_type.value for record_type in RecordType}
        if record_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid record_type. Allowed: {', '.join(sorted(valid_types))}"
            )
        query = query.eq("record_type", record_type)
    
    query = query.order("created_at", desc=True).limit(limit)
    result = query.execute()

    records = result.data or []
    bucket = settings.patient_photo_bucket
    ttl = settings.patient_photo_signed_url_ttl_seconds
    for record in records:
        image_path = record.get("image_path")
        if image_path:
            try:
                signed = supabase.storage.from_(bucket).create_signed_url(image_path, ttl)
            except Exception:
                signed = None
            signed_url = None
            if isinstance(signed, dict):
                signed_url = (
                    signed.get("signedURL")
                    or signed.get("signed_url")
                    or (signed.get("data") or {}).get("signedURL")
                    or (signed.get("data") or {}).get("signed_url")
                )
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
        "records": records
    }


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
    total_patients = patients_result.count if hasattr(patients_result, 'count') else 0
    
    # Urgent cases
    urgent_query = supabase.table("patients").select("id", count="exact").eq(
        "triage_priority", "urgent"
    )
    if doctor_id:
        urgent_query = urgent_query.eq("assigned_doctor_id", doctor_id)
    
    urgent_result = urgent_query.execute()
    urgent_cases = urgent_result.count if hasattr(urgent_result, 'count') else 0
    
    # High priority
    high_query = supabase.table("patients").select("id", count="exact").eq(
        "triage_priority", "high"
    )
    if doctor_id:
        high_query = high_query.eq("assigned_doctor_id", doctor_id)
    
    high_result = high_query.execute()
    high_priority = high_result.count if hasattr(high_result, 'count') else 0
    
    # Active consultations
    active_consults = supabase.table("consultations").select(
        "id", count="exact"
    ).in_(
        "status", ["triage", "urgent"]
    ).execute()
    
    pending_consultations = active_consults.count if hasattr(active_consults, 'count') else 0
    
    return {
        "total_patients": total_patients,
        "urgent_cases": urgent_cases,
        "high_priority": high_priority,
        "pending_consultations": pending_consultations,
        "alerts": urgent_cases + high_priority
    }
