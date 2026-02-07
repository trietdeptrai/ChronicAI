"""
Doctor Router - Endpoints for doctor-specific functionality.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from app.db.database import get_supabase
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
    
    # Get total count
    count_result = supabase.table("patients").select(
        "id", count="exact"
    ).execute()
    
    total = count_result.count if hasattr(count_result, 'count') else len(result.data)
    
    return {
        "patients": result.data or [],
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
    
    return {
        "patient": patient.data,
        "recent_vitals": vitals.data or [],
        "recent_consultations": consultations.data or []
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
        "is_verified, created_at"
    ).eq("patient_id", str(patient_uuid))
    
    if record_type:
        valid_types = ["prescription", "lab", "xray", "ecg", "notes", "referral"]
        if record_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid record_type. Allowed: {', '.join(valid_types)}"
            )
        query = query.eq("record_type", record_type)
    
    query = query.order("created_at", desc=True).limit(limit)
    result = query.execute()
    
    return {
        "patient_id": patient_id,
        "records": result.data or []
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
