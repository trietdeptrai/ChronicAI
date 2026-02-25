"""
Doctor Router - Endpoints for doctor-specific functionality.
"""
from __future__ import annotations

import asyncio
from difflib import SequenceMatcher
import io
import json
import logging
import re
import tempfile
import threading
import textwrap
import unicodedata
import zipfile
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db.database import get_supabase
from app.models.schemas import (
    BloodType,
    ClinicalSummaryRequest,
    ClinicalSummaryResponse,
    ExportLanguage,
    GenderType,
    GlucoseTiming,
    LanguagePref,
    PatientCreateRequest,
    PatientMetadataExportRequest,
    PatientTextExportFormat,
    PatientUpdateRequest,
    ProfileStatus,
    RecordType,
    TriagePriority,
    VitalSignCreateRequest,
    VitalSource,
)
from app.services.ocr import OCRDependencyError, extract_text
from app.services.llm import generate_clinical_summary, generate_patient_profile_summary

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
    "insurance_number",
}

MEDICAL_HISTORY_FAMILY_FALLBACK_KEYS = {
    "hospitalizations",
    "medications_history",
    "psychiatric_history",
}
IMMUNIZATION_FAMILY_FALLBACK_KEYS = {
    "vaccines_administered",
    "vaccines_due",
}
TREATMENT_HISTORY_FAMILY_FALLBACK_KEYS = {
    "previous_treatments",
    "physiotherapy",
    "other_relevant_treatments",
}
_HISTORY_VALUE_MISSING = object()






GLOBAL_IMPORT_ALLOWED_EXTENSIONS = {".zip"}
SUBDATA_IMPORT_ALLOWED_EXTENSIONS = {".json", ".pdf"}
IMMUTABLE_PATIENT_IMPORT_FIELDS = {
    "id",
    "user_id",
    "created_at",
    "updated_at",
    "bmi",
}
PATIENT_IMPORT_JSON_FIELDS = {
    "chronic_conditions",
    "current_medications",
    "allergies",
    "surgical_history",
    "family_medical_history",
    "medical_history",
    "immunization_records",
    "treatment_history",
    "notification_preferences",
}
PATIENT_IMPORT_FLOAT_FIELDS = {"height_cm", "weight_kg"}
PATIENT_IMPORT_INT_FIELDS = {"medication_adherence_score"}
PATIENT_IMPORT_BOOL_FIELDS = set()
VITAL_IMPORT_INT_FIELDS = {
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "heart_rate",
    "oxygen_saturation",
}
VITAL_IMPORT_FLOAT_FIELDS = {"blood_glucose", "temperature", "weight_kg"}
MEDICAL_HISTORY_PREFILL_KEYS = [
    "chronic_conditions",
    "past_surgeries",
    "hospitalizations",
    "medications_history",
    "allergies",
    "psychiatric_history",
    "family_history_of_chronic_conditions",
    "family_history_of_mental_health_conditions",
    "family_history_of_genetic_conditions",
    "vaccines_administered",
    "vaccines_due",
    "previous_treatments",
    "physiotherapy",
    "other_relevant_treatments",
]
MEDICAL_HISTORY_PDF_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Personal Medical History",
        [
            "chronic_conditions",
            "past_surgeries",
            "hospitalizations",
            "medications_history",
            "allergies",
            "psychiatric_history",
        ],
    ),
    (
        "Family Medical History",
        [
            "family_history_of_chronic_conditions",
            "family_history_of_mental_health_conditions",
            "family_history_of_genetic_conditions",
        ],
    ),
    (
        "Immunization History",
        [
            "vaccines_administered",
            "vaccines_due",
        ],
    ),
    (
        "Treatment History",
        [
            "previous_treatments",
            "physiotherapy",
            "other_relevant_treatments",
        ],
    ),
]
MEDICAL_HISTORY_ITEM_PREFERRED_KEYS = [
    "name",
    "title",
    "condition",
    "icd10_code",
    "diagnosed_date",
    "date",
    "status",
    "severity",
    "stage",
    "notes",
]
MEDICAL_HISTORY_SECTION_PATIENT_KEYS = {
    "chronic_conditions",
    "surgical_history",
    "allergies",
    "medical_history",
    "family_medical_history",
    "immunization_records",
    "treatment_history",
}
PDF_MEDICAL_HISTORY_FIELD_LABELS: dict[str, str] = {
    "chronic_conditions": "Chronic Conditions",
    "past_surgeries": "Past Surgeries",
    "hospitalizations": "Hospitalizations",
    "medications_history": "Medications History",
    "allergies": "Allergies",
    "psychiatric_history": "Psychiatric History",
    "family_history_of_chronic_conditions": "Family History of Chronic Conditions",
    "family_history_of_mental_health_conditions": "Family History of Mental Health Conditions",
    "family_history_of_genetic_conditions": "Family History of Genetic Conditions",
    "vaccines_administered": "Vaccines Administered",
    "vaccines_due": "Vaccines Due",
    "previous_treatments": "Previous Treatments",
    "physiotherapy": "Physiotherapy",
    "other_relevant_treatments": "Other Relevant Treatments",
}
PATIENT_METADATA_IMPORT_FIELDS = {
    "full_name",
    "date_of_birth",
    "gender",
    "national_id",
    "insurance_number",
    "primary_diagnosis",
    "phone_primary",
    "email",
    "address_ward",
    "address_district",
    "address_province",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    "triage_priority",
    "profile_status",
}
PATIENT_METADATA_ENUM_OPTIONS: dict[str, set[str]] = {
    "gender": {"male", "female", "other"},
    "triage_priority": {item.value for item in TriagePriority},
    "profile_status": {item.value for item in ProfileStatus},
}
PDF_METADATA_FIELD_LABELS: dict[str, str] = {
    "full_name": "Full Name",
    "date_of_birth": "Date of Birth",
    "gender": "Gender",
    "national_id": "NRIC",
    "insurance_number": "Health Insurance Number",
    "primary_diagnosis": "Diagnosis",
    "phone_primary": "Primary Phone",
    "email": "Email",
    "address_ward": "Ward",
    "address_district": "District",
    "address_province": "Province",
    "emergency_contact_name": "Emergency Contact Name",
    "emergency_contact_phone": "Emergency Contact Phone",
    "emergency_contact_relationship": "Emergency Contact Relationship",
    "triage_priority": "Triage Priority",
    "profile_status": "Profile Status",
}
PDF_VITAL_FIELD_LABELS: dict[str, str] = {
    "id": "Vital ID",
    "recorded_at": "Recorded At",
    "recorded_by": "Recorded By",
    "blood_pressure_systolic": "Systolic BP (mmHg)",
    "blood_pressure_diastolic": "Diastolic BP (mmHg)",
    "heart_rate": "Heart Rate (bpm)",
    "blood_glucose": "Blood Glucose",
    "blood_glucose_timing": "Glucose Timing",
    "temperature": "Temperature (C)",
    "oxygen_saturation": "SpO2 (%)",
    "weight_kg": "Weight (kg)",
    "notes": "Notes",
    "source": "Source",
    "created_at": "Created At",
}
PDF_PATIENT_FIELD_LABELS: dict[str, str] = {
    **PDF_METADATA_FIELD_LABELS,
    "id": "Patient ID",
    "user_id": "Linked User ID",
    "national_id": "National ID",
    "phone_secondary": "Secondary Phone",
    "address_street": "Street",
    "profile_photo_url": "Profile Photo URL",
    "blood_type": "Blood Type",
    "height_cm": "Height (cm)",
    "weight_kg": "Weight (kg)",
    "bmi": "BMI",
    "primary_diagnosis": "Primary Diagnosis",
    "diagnosis_date": "Diagnosis Date",
    "disease_stage": "Disease Stage",
    "chronic_conditions": "Chronic Conditions",
    "current_medications": "Current Medications",
    "medication_adherence_score": "Medication Adherence Score",
    "allergies": "Allergies",
    "smoking_status": "Smoking Status",
    "alcohol_consumption": "Alcohol Consumption",
    "insurance_provider": "Insurance Provider",
    "insurance_number": "Insurance Number",
    "insurance_expiry": "Insurance Expiry",
    "preferred_language": "Preferred Language",
    "assigned_doctor_id": "Assigned Doctor ID",
    "last_checkup_date": "Last Checkup Date",
    "next_appointment_date": "Next Appointment Date",
    "created_at": "Created At",
    "updated_at": "Updated At",
}
PDF_CONSULTATION_FIELD_LABELS: dict[str, str] = {
    "id": "Consultation ID",
    "doctor_id": "Doctor ID",
    "chief_complaint": "Chief Complaint",
    "status": "Status",
    "priority": "Priority",
    "started_at": "Started At",
    "ended_at": "Ended At",
    "duration_minutes": "Duration (minutes)",
    "messages": "Messages",
    "summary": "Summary",
    "clinical_notes": "Clinical Notes",
    "follow_up_required": "Follow-up Required",
    "follow_up_date": "Follow-up Date",
    "follow_up_notes": "Follow-up Notes",
    "created_at": "Created At",
    "updated_at": "Updated At",
}
PDF_RECORD_FIELD_LABELS: dict[str, str] = {
    "id": "Record ID",
    "doctor_id": "Doctor ID",
    "record_type": "Record Type",
    "title": "Title",
    "content_text": "Content Text",
    "analysis_result": "AI Analysis",
    "is_verified": "Verified",
    "verified_by": "Verified By",
    "verified_at": "Verified At",
    "image_path": "Storage Path",
    "file_extension": "File Extension",
    "doctor_comment": "Doctor Comment",
    "created_at": "Created At",
    "updated_at": "Updated At",
}
PDF_METADATA_FIELD_LABELS_VI: dict[str, str] = {
    "full_name": "Họ và tên",
    "date_of_birth": "Ngày sinh",
    "gender": "Giới tính",
    "national_id": "Số CCCD",
    "insurance_number": "Mã số BHYT",
    "primary_diagnosis": "Chuẩn đoán",
    "phone_primary": "Số điện thoại chính",
    "email": "Email",
    "address_ward": "Phường/Xã",
    "address_district": "Quận/Huyện",
    "address_province": "Tỉnh/Thành phố",
    "emergency_contact_name": "Người liên hệ khẩn cấp",
    "emergency_contact_phone": "Số điện thoại khẩn cấp",
    "emergency_contact_relationship": "Mối quan hệ khẩn cấp",
    "triage_priority": "Mức ưu tiên",
    "profile_status": "Trạng thái hồ sơ",
}
PDF_VITAL_FIELD_LABELS_VI: dict[str, str] = {
    "id": "Mã chỉ số",
    "recorded_at": "Thời gian đo",
    "recorded_by": "Người ghi nhận",
    "blood_pressure_systolic": "Huyết áp tâm thu (mmHg)",
    "blood_pressure_diastolic": "Huyết áp tâm trương (mmHg)",
    "heart_rate": "Nhịp tim (bpm)",
    "blood_glucose": "Đường huyết",
    "blood_glucose_timing": "Thời điểm đo đường huyết",
    "temperature": "Nhiệt độ (C)",
    "oxygen_saturation": "SpO2 (%)",
    "weight_kg": "Cân nặng (kg)",
    "notes": "Ghi chú",
    "source": "Nguồn dữ liệu",
    "created_at": "Thời gian tạo",
}
PDF_PATIENT_FIELD_LABELS_VI: dict[str, str] = {
    **PDF_METADATA_FIELD_LABELS_VI,
    "id": "Mã bệnh nhân",
    "user_id": "Mã người dùng liên kết",
    "national_id": "Số CCCD/CMND",
    "phone_secondary": "Số điện thoại phụ",
    "address_street": "Đường",
    "profile_photo_url": "Ảnh hồ sơ",
    "blood_type": "Nhóm máu",
    "height_cm": "Chiều cao (cm)",
    "weight_kg": "Cân nặng (kg)",
    "bmi": "BMI",
    "primary_diagnosis": "Chẩn đoán chính",
    "diagnosis_date": "Ngày chẩn đoán",
    "disease_stage": "Giai đoạn bệnh",
    "chronic_conditions": "Bệnh nền",
    "current_medications": "Thuốc đang dùng",
    "medication_adherence_score": "Điểm tuân thủ dùng thuốc",
    "allergies": "Dị ứng",
    "smoking_status": "Tình trạng hút thuốc",
    "alcohol_consumption": "Mức sử dụng rượu bia",
    "insurance_provider": "Đơn vị bảo hiểm",
    "insurance_number": "Số bảo hiểm",
    "insurance_expiry": "Ngày hết hạn bảo hiểm",
    "preferred_language": "Ngôn ngữ ưu tiên",
    "assigned_doctor_id": "Bác sĩ phụ trách",
    "last_checkup_date": "Ngày khám gần nhất",
    "next_appointment_date": "Ngày hẹn tiếp theo",
    "created_at": "Thời gian tạo",
    "updated_at": "Thời gian cập nhật",
}
PDF_CONSULTATION_FIELD_LABELS_VI: dict[str, str] = {
    "id": "Mã hội chẩn",
    "doctor_id": "Mã bác sĩ",
    "chief_complaint": "Lý do khám",
    "status": "Trạng thái",
    "priority": "Mức độ ưu tiên",
    "started_at": "Bắt đầu",
    "ended_at": "Kết thúc",
    "duration_minutes": "Thời lượng (phút)",
    "messages": "Trao đổi",
    "summary": "Tóm tắt",
    "clinical_notes": "Ghi chú lâm sàng",
    "follow_up_required": "Cần tái khám",
    "follow_up_date": "Ngày tái khám",
    "follow_up_notes": "Ghi chú tái khám",
    "created_at": "Thời gian tạo",
    "updated_at": "Thời gian cập nhật",
}
PDF_RECORD_FIELD_LABELS_VI: dict[str, str] = {
    "id": "Mã hồ sơ",
    "doctor_id": "Mã bác sĩ",
    "record_type": "Loại hồ sơ",
    "title": "Tiêu đề",
    "content_text": "Nội dung",
    "analysis_result": "Phân tích AI",
    "is_verified": "Đã xác thực",
    "verified_by": "Người xác thực",
    "verified_at": "Thời gian xác thực",
    "image_path": "Đường dẫn tệp",
    "file_extension": "Định dạng tệp",
    "doctor_comment": "Nhận xét bác sĩ",
    "created_at": "Thời gian tạo",
    "updated_at": "Thời gian cập nhật",
}
PDF_TEXT_BY_LANGUAGE: dict[str, dict[str, str]] = {
    "en": {
        "patient_record_export": "ChronicAI Patient Record Export",
        "vital_export": "ChronicAI Vital Signs Export",
        "metadata_export": "ChronicAI Patient Metadata Export",
        "exported_at": "Exported at",
        "patient_id": "Patient ID",
        "data_type": "Data Type",
        "summary": "Summary",
        "total_entries": "Total entries",
        "total_fields": "Total fields",
        "treatment_records": "Treatment Records",
        "vital_signs": "Vital Signs",
        "consultations": "Consultations",
        "medical_records": "Medical Records",
        "patient_profile": "Patient Profile",
        "vital_entry": "Vital Entry",
        "consultation_entry": "Consultation",
        "record_entry": "Record",
        "no_patient_profile_data": "No patient profile data.",
        "no_vital_signs_data": "No vital signs data.",
        "no_consultations_data": "No consultations data.",
        "no_medical_records_data": "No medical records data.",
        "no_metadata_fields": "No metadata fields.",
        "none": "None",
        "yes": "Yes",
        "no": "No",
        "demographics": "Demographics",
        "contact_information": "Contact Information",
        "emergency_contact": "Emergency Contact",
        "clinical_status": "Clinical Status",
        "lifestyle_and_risk": "Lifestyle and Risk",
        "insurance": "Insurance",
        "medical_background": "Medical Background",
        "additional_profile_data": "Additional Profile Data",
    },
    "vi": {
        "patient_record_export": "Báo cáo hồ sơ bệnh nhân ChronicAI",
        "vital_export": "Báo cáo chỉ số sinh tồn ChronicAI",
        "metadata_export": "Báo cáo metadata bệnh nhân ChronicAI",
        "exported_at": "Thời điểm xuất",
        "patient_id": "Mã bệnh nhân",
        "data_type": "Loại dữ liệu",
        "summary": "Tóm tắt",
        "total_entries": "Tổng số bản ghi",
        "total_fields": "Tổng số trường",
        "treatment_records": "Hồ sơ điều trị",
        "vital_signs": "Chỉ số sinh tồn",
        "consultations": "Hội chẩn",
        "medical_records": "Hồ sơ y khoa",
        "patient_profile": "Thông tin bệnh nhân",
        "vital_entry": "Bản ghi sinh tồn",
        "consultation_entry": "Lần hội chẩn",
        "record_entry": "Hồ sơ",
        "no_patient_profile_data": "Không có thông tin hồ sơ bệnh nhân.",
        "no_vital_signs_data": "Không có dữ liệu chỉ số sinh tồn.",
        "no_consultations_data": "Không có dữ liệu hội chẩn.",
        "no_medical_records_data": "Không có dữ liệu hồ sơ y khoa.",
        "no_metadata_fields": "Không có trường metadata.",
        "none": "Không có",
        "yes": "Có",
        "no": "Không",
        "demographics": "Nhân khẩu học",
        "contact_information": "Thông tin liên hệ",
        "emergency_contact": "Liên hệ khẩn cấp",
        "clinical_status": "Tình trạng lâm sàng",
        "lifestyle_and_risk": "Lối sống và nguy cơ",
        "insurance": "Bảo hiểm",
        "medical_background": "Tiền sử y khoa",
        "additional_profile_data": "Thông tin bổ sung",
    },
}
PDF_PATIENT_PREFERRED_ORDER = [
    "full_name",
    "date_of_birth",
    "gender",
    "phone_primary",
    "email",
    "address_ward",
    "address_district",
    "address_province",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    "triage_priority",
    "profile_status",
]
PDF_VITAL_PREFERRED_ORDER = [
    "recorded_at",
    "source",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "heart_rate",
    "oxygen_saturation",
    "temperature",
    "weight_kg",
    "blood_glucose",
    "blood_glucose_timing",
    "notes",
]
TEST_RESULT_RECORD_TYPES = {"lab", "xray", "ecg", "ct", "mri"}
IMPORT_JOB_TTL_SECONDS = 60 * 60
IMPORT_JOB_MAX_ENTRIES = 200
_patient_import_jobs: dict[str, dict[str, Any]] = {}
_patient_import_jobs_lock = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _prune_patient_import_jobs_locked() -> None:
    now_ts = datetime.utcnow().timestamp()

    stale_job_ids: list[str] = []
    for job_id, job in _patient_import_jobs.items():
        status_value = str(job.get("status") or "")
        updated_at_raw = job.get("updated_at")
        try:
            updated_at_ts = datetime.fromisoformat(str(updated_at_raw).replace("Z", "")).timestamp()
        except Exception:
            updated_at_ts = now_ts

        if status_value in {"completed", "failed"} and (now_ts - updated_at_ts) > IMPORT_JOB_TTL_SECONDS:
            stale_job_ids.append(job_id)

    for job_id in stale_job_ids:
        _patient_import_jobs.pop(job_id, None)

    if len(_patient_import_jobs) <= IMPORT_JOB_MAX_ENTRIES:
        return

    ordered = sorted(
        _patient_import_jobs.items(),
        key=lambda item: str(item[1].get("updated_at") or ""),
    )
    overflow = len(_patient_import_jobs) - IMPORT_JOB_MAX_ENTRIES
    for job_id, _ in ordered[:overflow]:
        _patient_import_jobs.pop(job_id, None)


def _create_patient_import_job(*, patient_id: str, import_format: str, file_name: str) -> dict[str, Any]:
    with _patient_import_jobs_lock:
        _prune_patient_import_jobs_locked()
        job_id = str(uuid4())
        now_iso = _utc_now_iso()
        job = {
            "job_id": job_id,
            "patient_id": patient_id,
            "import_format": import_format,
            "file_name": file_name,
            "status": "queued",
            "stage": "Queued",
            "progress": 0,
            "created_at": now_iso,
            "updated_at": now_iso,
            "ocr_current_page": None,
            "ocr_total_pages": None,
            "result": None,
            "error": None,
        }
        _patient_import_jobs[job_id] = job
        return dict(job)


def _update_patient_import_job(job_id: str, **updates: Any) -> dict[str, Any]:
    with _patient_import_jobs_lock:
        job = _patient_import_jobs.get(job_id)
        if not job:
            raise KeyError(job_id)
        for key, value in updates.items():
            if value is not None:
                job[key] = value
        if "progress" in updates and updates.get("progress") is not None:
            progress_value = int(max(0, min(100, int(updates["progress"]))))
            job["progress"] = progress_value
        job["updated_at"] = _utc_now_iso()
        return dict(job)


def _get_patient_import_job(job_id: str) -> Optional[dict[str, Any]]:
    with _patient_import_jobs_lock:
        job = _patient_import_jobs.get(job_id)
        if not job:
            return None
        return dict(job)


def _normalize_pdf_key(value: str) -> str:
    raw = str(value or "").strip().lower()
    # Preserve Vietnamese letters by removing diacritics to ASCII base characters first.
    deaccented = "".join(
        ch for ch in unicodedata.normalize("NFKD", raw)
        if not unicodedata.combining(ch)
    )
    normalized = re.sub(r"[^A-Za-z0-9_ ]+", "", deaccented)
    normalized = re.sub(r"\s+", "_", normalized).strip("_")
    return normalized


def _strip_pdf_heading_prefix(value: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\s*[\)\.\-]?\s*", "", str(value or "").strip())


def _coerce_nullable_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if _is_null_import_text(text):
        return None
    return text


def _parse_json_like_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    if text.lower() in {"none", "null"}:
        return None
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            return json.loads(text)
        except Exception:
            return text
    return text


IMPORT_NULL_PLACEHOLDERS = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "-",
    "--",
    "---",
    "_",
    "__",
    "___",
    "-.-",
    "--.--",
    "-,-",
    "-.-.-",
    "–",
    "—",
}


def _is_null_import_text(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in IMPORT_NULL_PLACEHOLDERS


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if _is_null_import_text(text):
        return None
    normalized_text = text.replace(" ", "")
    if re.fullmatch(r"[-_.,?\u2013\u2014]+", normalized_text):
        return None
    numeric_match = re.search(r"-?\d+(?:[.,]\d+)?", normalized_text)
    candidate = numeric_match.group(0) if numeric_match else normalized_text
    if "," in candidate and "." not in candidate:
        candidate = candidate.replace(",", ".")
    try:
        return int(float(candidate))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid integer value: {value}",
        ) from exc


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if _is_null_import_text(text):
        return None
    normalized_text = text.replace(" ", "")
    if re.fullmatch(r"[-_.,?\u2013\u2014]+", normalized_text):
        return None
    numeric_match = re.search(r"-?\d+(?:[.,]\d+)?", normalized_text)
    candidate = numeric_match.group(0) if numeric_match else normalized_text
    if "," in candidate and "." not in candidate:
        candidate = candidate.replace(",", ".")
    try:
        return float(candidate)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid decimal value: {value}",
        ) from exc


def _coerce_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    if _is_null_import_text(text):
        return None
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid boolean value: {value}",
    )


def _parse_patient_import_json_payload(raw_bytes: bytes) -> dict[str, Any]:
    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="JSON import file must be UTF-8 encoded.",
        ) from exc

    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON import file: {exc.msg}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="JSON import payload must be an object.",
        )
    return payload


def _append_continuation_value(container: dict[str, Any], key: Optional[str], line: str) -> None:
    if not key or key not in container:
        return
    previous = container.get(key)
    if previous is None:
        container[key] = line
        return
    container[key] = f"{previous} {line}".strip()


def _parse_patient_import_pdf_payload(ocr_text: str) -> dict[str, Any]:
    cleaned_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in ocr_text.splitlines()
        if str(line or "").strip()
    ]

    if not cleaned_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OCR returned no readable content from PDF import file.",
        )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "patient": {},
        "vitals": [],
        "consultations": [],
        "records": [],
    }
    expected_counts: dict[str, Optional[int]] = {
        "vitals": None,
        "consultations": None,
        "records": None,
    }

    section = "header"
    current_item: Optional[dict[str, Any]] = None
    current_item_key: Optional[str] = None
    current_patient_key: Optional[str] = None
    section_map = {
        "vitals": "vitals",
        "consultations": "consultations",
        "records": "records",
    }
    section_prefix = r"(?:\d+(?:\.\d+)*\s*[\)\.\-]?\s*)?"
    patient_heading_keys: set[str] = set()
    for language_map in PDF_TEXT_BY_LANGUAGE.values():
        for heading_key in (
            "summary",
            "demographics",
            "contact_information",
            "emergency_contact",
            "clinical_status",
            "lifestyle_and_risk",
            "insurance",
            "medical_background",
            "additional_profile_data",
        ):
            heading = language_map.get(heading_key)
            if heading:
                patient_heading_keys.add(_normalize_pdf_key(_strip_pdf_heading_prefix(heading)))
    patient_heading_keys.update({
        _normalize_pdf_key(section_title)
        for section_title, _ in MEDICAL_HISTORY_PDF_GROUPS
    })

    def flush_item() -> None:
        nonlocal current_item, current_item_key
        if current_item and section in section_map:
            payload[section_map[section]].append(current_item)
        current_item = None
        current_item_key = None

    for raw_line in cleaned_lines:
        line = raw_line.strip()
        if not line:
            continue

        if re.match(r"^[-=]{3,}$", line):
            current_patient_key = None
            current_item_key = None
            continue

        stripped_line = _strip_pdf_heading_prefix(line)
        normalized_section_key = _normalize_pdf_key(stripped_line)

        if normalized_section_key == "patient_profile":
            flush_item()
            section = "patient"
            current_patient_key = None
            continue

        if normalized_section_key.endswith("treatment_records"):
            flush_item()
            section = "treatment"
            current_patient_key = None
            continue
        if (
            normalized_section_key.endswith("regular_checkups")
            or normalized_section_key.endswith("medical_test_results")
            or normalized_section_key.endswith("medical_records_test_results")
            or normalized_section_key.endswith("medical_history")
        ):
            # Informational subsection headers in newer export layouts.
            flush_item()
            section = "treatment"
            current_patient_key = None
            continue

        if (
            normalized_section_key in {"consultations", "medical_records", "medical_history", "vital_signs"}
            and not re.search(r"\(\d+\)\s*$", line)
            and ":" not in line
        ):
            current_patient_key = None
            current_item_key = None
            continue

        if section == "patient" and normalized_section_key in patient_heading_keys and ":" not in line:
            current_patient_key = None
            continue

        vital_header = re.match(rf"^{section_prefix}vital\s*signs\s*\((\d+)\)$", line, flags=re.IGNORECASE)
        if vital_header:
            flush_item()
            section = "vitals"
            expected_counts["vitals"] = int(vital_header.group(1))
            current_patient_key = None
            continue

        consultation_header = re.match(rf"^{section_prefix}consultations\s*\((\d+)\)$", line, flags=re.IGNORECASE)
        if consultation_header:
            flush_item()
            section = "consultations"
            expected_counts["consultations"] = int(consultation_header.group(1))
            current_patient_key = None
            continue

        record_header = re.match(rf"^{section_prefix}medical\s*records\s*\((\d+)\)$", line, flags=re.IGNORECASE)
        if record_header:
            flush_item()
            section = "records"
            expected_counts["records"] = int(record_header.group(1))
            current_patient_key = None
            continue

        if re.match(rf"^{section_prefix}vital(?:\s*entry)?\s*#\d+$", line, flags=re.IGNORECASE):
            flush_item()
            section = "vitals"
            current_item = {}
            continue

        if re.match(rf"^{section_prefix}consultation(?:\s*entry)?\s*#\d+$", line, flags=re.IGNORECASE):
            flush_item()
            section = "consultations"
            current_item = {}
            continue

        if re.match(rf"^{section_prefix}record(?:\s*entry)?\s*#\d+$", line, flags=re.IGNORECASE):
            flush_item()
            section = "records"
            current_item = {}
            continue

        if re.match(rf"^{section_prefix}no\s+.+\s+data\.$", line, flags=re.IGNORECASE):
            continue

        match = re.match(r"^([^:]+):\s*(.*)$", line)
        if match:
            key = _normalize_pdf_key(_strip_pdf_heading_prefix(match.group(1)))
            value = match.group(2).strip()
            if not key:
                continue

            if section == "header":
                if key == "exported_at":
                    payload["exported_at"] = value
                elif key == "patient_id":
                    payload["patient_id"] = value
                continue

            if section == "patient":
                payload["patient"][key] = value
                current_patient_key = key
                continue

            if section in section_map and current_item is not None:
                current_item[key] = value
                current_item_key = key
            continue

        if section == "patient":
            _append_continuation_value(payload["patient"], current_patient_key, line)
            continue
        if section in section_map and current_item is not None:
            _append_continuation_value(current_item, current_item_key, line)

    flush_item()

    for key, expected in expected_counts.items():
        if expected is None:
            continue
        actual = len(payload.get(key, []))
        if actual != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"PDF OCR parsing mismatch for {key}: expected {expected}, got {actual}. "
                    "Please retry with JSON import for lossless recovery."
                ),
            )

    return payload


def _normalize_patient_import_field(key: str, value: Any) -> Any:
    if key in PATIENT_IMPORT_JSON_FIELDS:
        return _parse_json_like_text(value)
    if key in PATIENT_IMPORT_FLOAT_FIELDS:
        return _coerce_optional_float(value)
    if key in PATIENT_IMPORT_INT_FIELDS:
        return _coerce_optional_int(value)
    if key in PATIENT_IMPORT_BOOL_FIELDS:
        return _coerce_optional_bool(value)

    if isinstance(value, str):
        if key in {
            "gender",
            "triage_priority",
            "profile_status",
            "preferred_language",
            "smoking_status",
            "alcohol_consumption",
            "exercise_frequency",
            "insurance_coverage_level",
        }:
            text = _coerce_nullable_text(value)
            return text.lower() if text else None
        if key == "blood_type":
            text = _coerce_nullable_text(value)
            return text.upper() if text else None
        return _coerce_nullable_text(value)
    return value


def _normalize_vital_import_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    source_value = _coerce_nullable_text(raw_row.get("source"))
    if source_value and source_value not in {source.value for source in VitalSource}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid vital source value: {source_value}",
        )

    timing_value = _coerce_nullable_text(raw_row.get("blood_glucose_timing"))
    if timing_value and timing_value not in {timing.value for timing in GlucoseTiming}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid blood_glucose_timing value: {timing_value}",
        )

    row = {
        "id": _coerce_nullable_text(raw_row.get("id")),
        "recorded_at": _coerce_nullable_text(raw_row.get("recorded_at")),
        "recorded_by": _coerce_nullable_text(raw_row.get("recorded_by")),
        "blood_pressure_systolic": _coerce_optional_int(raw_row.get("blood_pressure_systolic")),
        "blood_pressure_diastolic": _coerce_optional_int(raw_row.get("blood_pressure_diastolic")),
        "heart_rate": _coerce_optional_int(raw_row.get("heart_rate")),
        "blood_glucose": _coerce_optional_float(raw_row.get("blood_glucose")),
        "blood_glucose_timing": timing_value,
        "temperature": _coerce_optional_float(raw_row.get("temperature")),
        "oxygen_saturation": _coerce_optional_int(raw_row.get("oxygen_saturation")),
        "weight_kg": _coerce_optional_float(raw_row.get("weight_kg")),
        "notes": _coerce_nullable_text(raw_row.get("notes")),
        "source": source_value or VitalSource.self_reported.value,
        "created_at": _coerce_nullable_text(raw_row.get("created_at")),
    }

    return {key: value for key, value in row.items() if value is not None}


def _normalize_consultation_import_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    status_value = _coerce_nullable_text(raw_row.get("status"))
    if status_value and status_value not in {"triage", "urgent", "stable", "resolved", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid consultation status value: {status_value}",
        )

    priority_value = _coerce_nullable_text(raw_row.get("priority"))
    if priority_value and priority_value not in {priority.value for priority in TriagePriority}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid consultation priority value: {priority_value}",
        )

    row = {
        "id": _coerce_nullable_text(raw_row.get("id")),
        "doctor_id": _coerce_nullable_text(raw_row.get("doctor_id")),
        "chief_complaint": _coerce_nullable_text(raw_row.get("chief_complaint")),
        "status": status_value,
        "priority": priority_value,
        "started_at": _coerce_nullable_text(raw_row.get("started_at")),
        "ended_at": _coerce_nullable_text(raw_row.get("ended_at")),
        "duration_minutes": _coerce_optional_int(raw_row.get("duration_minutes")),
        "messages": _parse_json_like_text(raw_row.get("messages")),
        "summary": _coerce_nullable_text(raw_row.get("summary")),
        "clinical_notes": _parse_json_like_text(raw_row.get("clinical_notes")),
        "follow_up_required": _coerce_optional_bool(raw_row.get("follow_up_required")),
        "follow_up_date": _coerce_nullable_text(raw_row.get("follow_up_date")),
        "follow_up_notes": _coerce_nullable_text(raw_row.get("follow_up_notes")),
        "created_at": _coerce_nullable_text(raw_row.get("created_at")),
        "updated_at": _coerce_nullable_text(raw_row.get("updated_at")),
    }
    return {key: value for key, value in row.items() if value is not None}


def _normalize_record_import_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    record_type = _coerce_nullable_text(raw_row.get("record_type"))
    if record_type and record_type not in {record.value for record in RecordType}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid medical record type value: {record_type}",
        )
    if not record_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each imported medical record requires record_type.",
        )

    row = {
        "id": _coerce_nullable_text(raw_row.get("id")),
        "doctor_id": _coerce_nullable_text(raw_row.get("doctor_id")),
        "record_type": record_type,
        "title": _coerce_nullable_text(raw_row.get("title")),
        "content_text": _coerce_nullable_text(raw_row.get("content_text")),
        "analysis_result": _parse_json_like_text(raw_row.get("analysis_result")),
        "is_verified": _coerce_optional_bool(raw_row.get("is_verified")),
        "verified_by": _coerce_nullable_text(raw_row.get("verified_by")),
        "verified_at": _coerce_nullable_text(raw_row.get("verified_at")),
        "image_path": _coerce_nullable_text(raw_row.get("image_path")),
        "doctor_comment": _coerce_nullable_text(raw_row.get("doctor_comment")),
        "created_at": _coerce_nullable_text(raw_row.get("created_at")),
        "updated_at": _coerce_nullable_text(raw_row.get("updated_at")),
    }
    return {key: value for key, value in row.items() if value is not None}


def _normalize_patient_import_payload(payload: dict[str, Any]) -> dict[str, Any]:
    patient_raw = payload.get("patient")
    if not isinstance(patient_raw, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Import payload is missing patient profile data.",
        )

    vitals_raw = payload.get("vitals") or []
    consultations_raw = payload.get("consultations") or []
    records_raw = payload.get("records") or []
    treatment_records_raw = payload.get("treatment_records") if isinstance(payload.get("treatment_records"), dict) else {}
    treatment_medical_history_raw = (
        treatment_records_raw.get("medical_history")
        if isinstance(treatment_records_raw.get("medical_history"), dict)
        else {}
    )
    patient = _merge_treatment_medical_history_into_patient(
        patient_raw,
        treatment_medical_history_raw,
    )

    if not vitals_raw and isinstance(treatment_records_raw.get("regular_checkups"), list):
        vitals_raw = treatment_records_raw.get("regular_checkups") or []
    if not records_raw:
        if isinstance(treatment_records_raw.get("medical_test_results"), list):
            records_raw = treatment_records_raw.get("medical_test_results") or []
        elif isinstance(treatment_records_raw.get("medical_records"), list):
            records_raw = treatment_records_raw.get("medical_records") or []

    if not isinstance(vitals_raw, list) or not isinstance(consultations_raw, list) or not isinstance(records_raw, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Import payload has invalid section structure.",
        )

    normalized_patient: dict[str, Any] = {}
    for key, value in patient.items():
        normalized_key = _normalize_pdf_key(key)
        if not normalized_key:
            continue
        normalized_patient[normalized_key] = _normalize_patient_import_field(normalized_key, value)

    normalized_vitals = [
        _normalize_vital_import_row(row)
        for row in vitals_raw
        if isinstance(row, dict)
    ]
    normalized_consultations = [
        _normalize_consultation_import_row(row)
        for row in consultations_raw
        if isinstance(row, dict)
    ]
    normalized_records = [
        _normalize_record_import_row(row)
        for row in records_raw
        if isinstance(row, dict)
    ]
    normalized_medical_history_section = _build_medical_history_section_payload(normalized_patient)

    return {
        "schema_version": payload.get("schema_version"),
        "patient_id": payload.get("patient_id"),
        "exported_at": payload.get("exported_at"),
        "patient": normalized_patient,
        "vitals": normalized_vitals,
        "consultations": normalized_consultations,
        "records": normalized_records,
        "treatment_records": {
            "regular_checkups": normalized_vitals,
            "medical_test_results": normalized_records,
            "medical_history": normalized_medical_history_section,
        },
    }


def _normalize_date_for_metadata(value: Any) -> Optional[str]:
    text = _coerce_nullable_text(value)
    if not text:
        return None

    candidate = text.strip()
    if len(candidate) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2}", candidate):
        return candidate[:10]

    try:
        if candidate.endswith("Z"):
            candidate = candidate[:-1]
        parsed = datetime.fromisoformat(candidate)
        return parsed.date().isoformat()
    except Exception:
        pass

    try:
        parsed_date = date.fromisoformat(candidate)
        return parsed_date.isoformat()
    except Exception:
        return text[:10] if len(text) >= 10 else text


def _normalize_patient_metadata_field(key: str, value: Any) -> Any:
    if key == "date_of_birth":
        return _normalize_date_for_metadata(value)

    text_value = _coerce_nullable_text(value)
    if text_value is None:
        return None

    if key in PATIENT_METADATA_ENUM_OPTIONS:
        normalized = text_value.lower()
        if normalized not in PATIENT_METADATA_ENUM_OPTIONS[key]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid value for {key}: {text_value}",
            )
        return normalized

    return text_value


def _normalize_patient_metadata_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in raw_payload.items():
        normalized_key = _normalize_pdf_key(key)
        if normalized_key not in PATIENT_METADATA_IMPORT_FIELDS:
            continue
        normalized_value = _normalize_patient_metadata_field(normalized_key, value)
        if normalized_value is not None:
            normalized[normalized_key] = normalized_value
    return normalized


def _parse_patient_metadata_json_payload(raw_bytes: bytes) -> dict[str, Any]:
    payload = _parse_patient_import_json_payload(raw_bytes)

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        return _normalize_patient_metadata_payload(metadata)

    return _normalize_patient_metadata_payload(payload)


def _parse_patient_metadata_pdf_payload(ocr_text: str) -> dict[str, Any]:
    cleaned_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in ocr_text.splitlines()
        if str(line or "").strip()
    ]

    if not cleaned_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OCR returned no readable content from metadata PDF import file.",
        )

    metadata: dict[str, Any] = {}
    current_key: Optional[str] = None
    header_keys = {
        "exported_at",
        "data_type",
        "schema_version",
        "patient_id",
    }
    metadata_field_aliases: dict[str, str] = {
        _normalize_pdf_key(field): field for field in PATIENT_METADATA_IMPORT_FIELDS
    }
    for label_map in (PDF_METADATA_FIELD_LABELS, PDF_METADATA_FIELD_LABELS_VI):
        for field, label in label_map.items():
            metadata_field_aliases[_normalize_pdf_key(label)] = field
            metadata_field_aliases[_normalize_pdf_key(_humanize_export_key(field))] = field

    for line in cleaned_lines:
        match = re.match(r"^([^:\uFF1A]+)\s*[:\uFF1A]\s*(.*)$", line)
        if match:
            raw_key = _normalize_pdf_key(match.group(1))
            resolved = _resolve_alias_key(raw_key, metadata_field_aliases)
            key = resolved or raw_key
            value = match.group(2).strip()
            if not key or key in header_keys:
                current_key = None
                continue
            if key in PATIENT_METADATA_IMPORT_FIELDS:
                metadata[key] = value
                current_key = key
            else:
                current_key = None
            continue

        if current_key:
            _append_continuation_value(metadata, current_key, line)

    normalized = _normalize_patient_metadata_payload(metadata)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse patient metadata fields from PDF import file.",
        )
    return normalized


def _vital_export_payload_to_pdf_lines(payload: dict[str, Any], export_language: str = "en") -> list[str]:
    text_map = _pdf_text(export_language)
    vital_label_map = _pdf_label_map("vital", export_language)
    vitals = payload.get("vitals") if isinstance(payload.get("vitals"), list) else []
    lines: list[str] = [
        text_map["vital_export"],
        f"{text_map['exported_at']}: {payload.get('exported_at', '')}",
        f"{text_map['patient_id']}: {payload.get('patient_id', '')}",
        "",
        text_map["summary"],
        f"{text_map['total_entries']}: {len(vitals)}",
        "",
        f"{text_map['vital_signs']} ({len(vitals)})",
    ]

    if not vitals:
        lines.append(text_map["no_vital_signs_data"])
        return lines

    for index, vital in enumerate(vitals, start=1):
        lines.append(f"{text_map['vital_entry']} #{index}")
        if isinstance(vital, dict):
            for key in _ordered_keys(vital, PDF_VITAL_PREFERRED_ORDER):
                _append_pdf_structured_field(
                    lines,
                    label=vital_label_map.get(key) or _humanize_export_key(key),
                    value=vital.get(key),
                    indent=2,
                    export_language=export_language,
                )
        else:
            lines.append(f"  {_as_export_text(vital)}")
        lines.append("")

    return lines


def _patient_metadata_payload_to_pdf_lines(metadata: dict[str, Any], export_language: str = "en") -> list[str]:
    text_map = _pdf_text(export_language)
    metadata_label_map = _pdf_label_map("metadata", export_language)
    lines: list[str] = [
        text_map["metadata_export"],
        f"{text_map['exported_at']}: {datetime.utcnow().isoformat()}Z",
        f"{text_map['data_type']}: patient_metadata",
        "",
        text_map["patient_profile"],
    ]
    if not metadata:
        lines.append(text_map["no_metadata_fields"])
        return lines

    lines.append(text_map["summary"])
    lines.append(f"{text_map['total_fields']}: {len(metadata)}")
    lines.append("")

    for key in _ordered_keys(metadata, PDF_PATIENT_PREFERRED_ORDER):
        _append_pdf_structured_field(
            lines,
            label=metadata_label_map.get(key) or _humanize_export_key(key),
            value=metadata.get(key),
            indent=0,
            export_language=export_language,
        )
    return lines


def _empty_medical_history_prefill() -> dict[str, list[Any]]:
    return {
        key: []
        for key in MEDICAL_HISTORY_PREFILL_KEYS
    }


def _coerce_medical_history_prefill_map(value: Any) -> dict[str, list[Any]]:
    if not isinstance(value, dict):
        return _empty_medical_history_prefill()
    return {
        key: _coerce_history_list(value.get(key))
        for key in MEDICAL_HISTORY_PREFILL_KEYS
    }


def _medical_history_export_payload_to_pdf_lines(
    payload: dict[str, Any],
    export_language: str = "en",
) -> list[str]:
    text_map = _pdf_text(export_language)
    history_label_map = _pdf_label_map("medical_history", export_language)
    section = (
        payload.get("medical_history_section")
        if isinstance(payload.get("medical_history_section"), dict)
        else {}
    )
    prefill = _coerce_medical_history_prefill_map(section.get("prefill"))
    if not any(_medical_history_prefill_has_value(prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        prefill = _build_medical_history_prefill(section)

    populated_fields = sum(
        1
        for key in MEDICAL_HISTORY_PREFILL_KEYS
        if _medical_history_prefill_has_value(prefill.get(key))
    )
    report_title = text_map.get("medical_history_export", "ChronicAI Medical History Report")
    lines: list[str] = [
        report_title,
        "=" * max(32, min(72, len(report_title))),
        f"{text_map['patient_id']}: {payload.get('patient_id', '')}",
        f"{text_map['exported_at']}: {payload.get('exported_at', '')}",
        f"{text_map['data_type']}: medical_history",
        "",
        text_map["summary"],
        f"{text_map['total_fields']}: {populated_fields}",
        "",
    ]

    if populated_fields == 0:
        lines.append(text_map.get("no_medical_history_data", "No medical history data."))
        return lines

    section_index = 1
    for section_title, keys in MEDICAL_HISTORY_PDF_GROUPS:
        populated_keys = [
            key for key in keys
            if _medical_history_prefill_has_value(prefill.get(key))
        ]
        if not populated_keys:
            continue
        lines.append(f"{section_index}. {section_title}")
        for key in populated_keys:
            _append_pdf_field_line(
                lines,
                key=key,
                value=_medical_history_values_to_pdf_text(prefill.get(key), export_language),
                label_map=history_label_map,
                indent=2,
            )
        lines.append("")
        section_index += 1

    if lines and not lines[-1]:
        lines.pop()

    return lines


def _parse_medical_history_import_json_payload(raw_bytes: bytes) -> dict[str, list[Any]]:
    payload = _parse_patient_import_json_payload(raw_bytes)

    explicit_prefill = payload.get("prefill")
    prefill = _coerce_medical_history_prefill_map(explicit_prefill)
    if any(_medical_history_prefill_has_value(prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        return prefill

    source: dict[str, Any]
    if isinstance(payload.get("medical_history_section"), dict):
        source = payload.get("medical_history_section")  # type: ignore[assignment]
    elif isinstance(payload.get("patient"), dict):
        source = payload.get("patient")  # type: ignore[assignment]
    else:
        source = payload

    nested_prefill = _coerce_medical_history_prefill_map(source.get("prefill"))
    if any(_medical_history_prefill_has_value(nested_prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        return nested_prefill

    prefill = _build_medical_history_prefill(source)
    if not any(_medical_history_prefill_has_value(prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid medical-history fields found in import file.",
        )
    return prefill


def _parse_medical_history_pdf_field_value(value: Any) -> list[Any]:
    parsed = _parse_json_like_text(value)
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return _coerce_history_list(parsed)
    if isinstance(parsed, dict):
        return [parsed]

    text = str(parsed).strip()
    if not text or _is_null_import_text(text):
        return []

    candidates: list[str] = []
    for raw_line in re.split(r"[\r\n]+", text):
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\u2022*]+\s*", "", line)
        line = re.sub(r"^\d+[)\.]\s*", "", line)
        if not line:
            continue
        parts = [part.strip() for part in line.split(";") if part.strip()]
        if parts:
            candidates.extend(parts)
        else:
            candidates.append(line)

    if candidates:
        return candidates
    return _coerce_history_list(parsed)


def _parse_medical_history_import_pdf_payload(ocr_text: str) -> dict[str, list[Any]]:
    cleaned_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in ocr_text.splitlines()
        if str(line or "").strip()
    ]
    if not cleaned_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OCR returned no readable content from medical-history PDF import file.",
        )

    field_aliases: dict[str, str] = {
        _normalize_pdf_key(key): key
        for key in MEDICAL_HISTORY_PREFILL_KEYS
    }
    for field, label in PDF_MEDICAL_HISTORY_FIELD_LABELS.items():
        field_aliases[_normalize_pdf_key(label)] = field
        field_aliases[_normalize_pdf_key(_humanize_export_key(field))] = field
    for label_map in (PDF_PATIENT_FIELD_LABELS, PDF_PATIENT_FIELD_LABELS_VI):
        for field in MEDICAL_HISTORY_PREFILL_KEYS:
            label = label_map.get(field)
            if label:
                field_aliases[_normalize_pdf_key(label)] = field

    ignored_headings = {
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("en").get("summary", "Summary"))),
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("vi").get("summary", "Summary"))),
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("en").get("medical_history", "Medical History"))),
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("vi").get("medical_history", "Medical History"))),
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("en").get("medical_history_export", "ChronicAI Medical History Report"))),
        _normalize_pdf_key(_strip_pdf_heading_prefix(_pdf_text("vi").get("medical_history_export", "Medical History Report"))),
    }
    for section_title, _ in MEDICAL_HISTORY_PDF_GROUPS:
        ignored_headings.add(_normalize_pdf_key(_strip_pdf_heading_prefix(section_title)))

    raw_values: dict[str, str] = {}
    current_key: Optional[str] = None

    for line in cleaned_lines:
        stripped_line = _strip_pdf_heading_prefix(line)
        normalized_line = _normalize_pdf_key(stripped_line)

        if re.match(r"^[-=]{3,}$", line):
            current_key = None
            continue
        if re.match(r"^-{2,}\s*(trang|page)\s*\d+\s*-{2,}$", stripped_line, flags=re.IGNORECASE):
            current_key = None
            continue
        if normalized_line in {"summary", "tom_tat"}:
            current_key = None
            continue
        if (
            normalized_line.startswith("chronic") and "medical_history_export" in normalized_line
        ) or normalized_line.startswith("bao_cao_tien_su_y_khoa"):
            current_key = None
            continue
        if normalized_line.startswith("total_fields") or normalized_line.startswith("tong_so_truong"):
            current_key = None
            continue
        if normalized_line in {
            "exported_at",
            "thoi_diem_xuat",
            "patient_id",
            "ma_benh_nhan",
            "medical_history",
            "tien_su_y_khoa",
        }:
            current_key = None
            continue
        if normalized_line in ignored_headings:
            current_key = None
            continue

        match = re.match(r"^([^:]+):\s*(.*)$", line)
        if match:
            raw_key = _normalize_pdf_key(_strip_pdf_heading_prefix(match.group(1)))
            resolved = _resolve_alias_key(raw_key, field_aliases)
            value = match.group(2).strip()
            if resolved:
                raw_values[resolved] = value
                current_key = resolved
            else:
                current_key = None
            continue

        if current_key:
            if re.match(r"^-{2,}.*-{2,}$", line):
                current_key = None
                continue
            previous = raw_values.get(current_key, "")
            raw_values[current_key] = f"{previous}\n{line}".strip()

    prefill: dict[str, list[Any]] = _empty_medical_history_prefill()
    for key in MEDICAL_HISTORY_PREFILL_KEYS:
        prefill[key] = _parse_medical_history_pdf_field_value(raw_values.get(key))

    if not any(_medical_history_prefill_has_value(prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse medical-history fields from PDF import file. Please retry with JSON import.",
        )
    return prefill


def _parse_vital_import_json_payload(raw_bytes: bytes) -> list[dict[str, Any]]:
    payload = _parse_patient_import_json_payload(raw_bytes)

    vitals_raw: list[Any]
    if isinstance(payload.get("vitals"), list):
        vitals_raw = payload.get("vitals") or []
    elif isinstance(payload.get("vital"), dict):
        vitals_raw = [payload.get("vital")]
    else:
        possible_single = {
            key: value for key, value in payload.items()
            if _normalize_pdf_key(key) in {
                "id",
                "recorded_at",
                "recorded_by",
                "blood_pressure_systolic",
                "blood_pressure_diastolic",
                "heart_rate",
                "blood_glucose",
                "blood_glucose_timing",
                "temperature",
                "oxygen_saturation",
                "weight_kg",
                "notes",
                "source",
                "created_at",
            }
        }
        vitals_raw = [possible_single] if possible_single else []

    normalized = [
        _normalize_vital_import_row(item)
        for item in vitals_raw
        if isinstance(item, dict)
    ]
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid vital sign entries found in import file.",
        )
    return normalized


def _parse_vital_import_pdf_payload(ocr_text: str) -> list[dict[str, Any]]:
    cleaned_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in ocr_text.splitlines()
        if str(line or "").strip()
    ]
    if not cleaned_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OCR returned no readable content from vital-sign PDF import file.",
        )
    no_data_markers = {
        "no vital signs data",
        "khong co du lieu chi so sinh ton",
    }
    if any(
        any(marker in _normalize_pdf_key(line).replace("_", " ") for marker in no_data_markers)
        for line in cleaned_lines
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Imported PDF contains no vital-sign entries.",
        )

    rows: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    current_key: Optional[str] = None
    header_keys = {"exported_at", "patient_id", "schema_version", "data_type"}
    vital_fields = {
        "id",
        "recorded_at",
        "recorded_by",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "heart_rate",
        "blood_glucose",
        "blood_glucose_timing",
        "temperature",
        "oxygen_saturation",
        "weight_kg",
        "notes",
        "source",
        "created_at",
    }
    vital_field_aliases: dict[str, str] = {
        _normalize_pdf_key(field): field for field in vital_fields
    }
    for label_map in (PDF_VITAL_FIELD_LABELS, PDF_VITAL_FIELD_LABELS_VI):
        for field, label in label_map.items():
            vital_field_aliases[_normalize_pdf_key(label)] = field
            vital_field_aliases[_normalize_pdf_key(_humanize_export_key(field))] = field

    def flush_current() -> None:
        nonlocal current, current_key
        if current:
            rows.append(current)
        current = None
        current_key = None

    for line in cleaned_lines:
        normalized_line = _normalize_pdf_key(line)

        # Ignore page separators/report headers that often appear between OCR pages.
        if re.match(r"^-{2,}\s*(trang|page)\s*\d+\s*-{2,}$", line, flags=re.IGNORECASE):
            current_key = None
            continue
        if normalized_line in {"summary", "tom_tat"}:
            current_key = None
            continue
        if (
            normalized_line.startswith("chronic") and "vital_signs_export" in normalized_line
        ) or normalized_line.startswith("bao_cao_chi_so_sinh_ton"):
            current_key = None
            continue
        if normalized_line.startswith("total_entries") or normalized_line.startswith("tong_so_ban_ghi"):
            current_key = None
            continue
        if normalized_line.startswith("vital_signs_") or normalized_line.startswith("chi_so_sinh_ton_"):
            current_key = None
            continue

        # OCR may render headings inconsistently; support EN + VI entry labels as row boundaries.
        entry_heading_tokens = ("vital", "sinh_ton", "chi_so_sinh_ton", "ban_ghi", "ghi_sinh")
        if (
            re.search(r"\d+", line)
            and not re.search(r"[:\uFF1A]", line)
            and (
                re.search(r"\bvital\b", line, flags=re.IGNORECASE)
                or normalized_line.startswith("vital_entry")
                or any(token in normalized_line for token in entry_heading_tokens)
            )
        ):
            flush_current()
            current = {}
            continue

        if line.lower().startswith("no vital") or normalized_line.startswith("khong_co_du_lieu_chi_so_sinh_ton"):
            continue

        match = re.match(r"^([^:：]+)\s*[:：]\s*(.*)$", line)
        if match:
            raw_key = _normalize_pdf_key(match.group(1))
            resolved = _resolve_alias_key(raw_key, vital_field_aliases)
            key = resolved or raw_key
            value = match.group(2).strip()
            if not key or key in header_keys:
                current_key = None
                continue
            if key in vital_fields:
                if current is None:
                    current = {}
                current[key] = value
                current_key = key
            else:
                current_key = None
            continue

        if current is not None and current_key:
            if re.match(r"^-{2,}.*-{2,}$", line):
                current_key = None
                continue
            _append_continuation_value(current, current_key, line)

    flush_current()

    normalized = [_normalize_vital_import_row(item) for item in rows if isinstance(item, dict)]
    if not normalized:
        logger.warning(
            "Vital PDF OCR parsing produced no entries. OCR sample=%s",
            " | ".join(cleaned_lines[:18]),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse vital-sign entries from PDF import file. Please retry with JSON import.",
        )
    return normalized


def _vital_row_to_prefill(row: dict[str, Any]) -> dict[str, Any]:
    recorded_at_value = _coerce_nullable_text(row.get("recorded_at"))
    recorded_at_prefill: Optional[str] = None
    if recorded_at_value:
        try:
            iso_candidate = recorded_at_value.replace("Z", "+00:00")
            parsed_dt = datetime.fromisoformat(iso_candidate)
            recorded_at_prefill = parsed_dt.strftime("%Y-%m-%dT%H:%M")
        except Exception:
            recorded_at_prefill = recorded_at_value[:16] if len(recorded_at_value) >= 16 else recorded_at_value

    source_value = _coerce_nullable_text(row.get("source")) or VitalSource.self_reported.value
    blood_glucose_timing = _coerce_nullable_text(row.get("blood_glucose_timing")) or ""

    def _num_to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    return {
        "recordedAt": recorded_at_prefill or "",
        "source": source_value,
        "bloodPressureSystolic": _num_to_text(row.get("blood_pressure_systolic")),
        "bloodPressureDiastolic": _num_to_text(row.get("blood_pressure_diastolic")),
        "heartRate": _num_to_text(row.get("heart_rate")),
        "bloodGlucose": _num_to_text(row.get("blood_glucose")),
        "bloodGlucoseTiming": blood_glucose_timing,
        "temperature": _num_to_text(row.get("temperature")),
        "oxygenSaturation": _num_to_text(row.get("oxygen_saturation")),
        "weightKg": _num_to_text(row.get("weight_kg")),
        "notes": _coerce_nullable_text(row.get("notes")) or "",
    }


def _guess_content_type(extension: str) -> str:
    mapping = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mapping.get(extension.lower(), "application/octet-stream")


def _log_ocr_debug_dump(context: str, raw_text: str) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    text = str(raw_text or "")
    numbered_lines = []
    for index, line in enumerate(text.splitlines(), start=1):
        numbered_lines.append(f"{index:04d}: {line}")
    line_dump = "\n".join(numbered_lines) if numbered_lines else "<empty OCR output>"
    logger.debug(
        "[ocr-debug] %s extracted_text_begin\n%s\n[ocr-debug] %s extracted_text_end",
        context,
        line_dump,
        context,
    )


def _replace_patient_table_rows(
    supabase: object,
    *,
    table_name: str,
    patient_uuid: UUID,
    rows: list[dict[str, Any]],
) -> int:
    patient_id = str(patient_uuid)
    try:
        supabase.table(table_name).delete().eq("patient_id", patient_id).execute()
    except Exception as exc:
        logger.exception("Failed to clear existing rows table=%s patient_id=%s", table_name, patient_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset existing {table_name} data before import.",
        ) from exc

    if not rows:
        return 0

    inserted_count = 0
    for index in range(0, len(rows), 200):
        batch = []
        for row in rows[index:index + 200]:
            batch_row = dict(row)
            batch_row["patient_id"] = patient_id
            batch.append(batch_row)
        try:
            result = supabase.table(table_name).insert(batch).execute()
        except Exception as exc:
            logger.exception("Failed to import rows table=%s patient_id=%s", table_name, patient_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import {table_name} data.",
            ) from exc
        inserted_count += len(result.data or batch)

    return inserted_count


def _sync_linked_user_contact(
    supabase: object,
    *,
    linked_user_id: Optional[str],
    patient_update_payload: dict[str, Any],
) -> None:
    if not linked_user_id:
        return

    user_update_payload: dict[str, Any] = {}
    if "phone_primary" in patient_update_payload:
        user_update_payload["phone_number"] = patient_update_payload["phone_primary"]
    if "email" in patient_update_payload:
        user_update_payload["email"] = patient_update_payload["email"]

    if not user_update_payload:
        return

    try:
        supabase.table("users").update(user_update_payload).eq(
            "id", str(linked_user_id)
        ).eq(
            "role", "patient"
        ).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number or email already exists on another user.",
            ) from exc
        logger.exception("Failed to sync linked user for patient import user_id=%s", linked_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync linked user information after import.",
        ) from exc


def _fetch_patient_record_storage_paths(supabase: object, *, patient_uuid: UUID) -> list[str]:
    try:
        result = supabase.table("medical_records").select("image_path").eq(
            "patient_id", str(patient_uuid)
        ).not_.is_(
            "image_path", "null"
        ).execute()
    except Exception:
        logger.exception("Failed to fetch existing record paths for patient import patient_id=%s", patient_uuid)
        return []

    rows = result.data or []
    paths: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        image_path = _coerce_nullable_text(row.get("image_path"))
        if image_path:
            paths.append(image_path)
    return paths


def _apply_patient_text_import(
    supabase: object,
    *,
    patient_uuid: UUID,
    payload: dict[str, Any],
    record_file_path_map: Optional[dict[str, str]] = None,
    clear_existing_record_files: bool = True,
) -> dict[str, int]:
    existing_result = supabase.table("patients").select("*").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    existing_patient = existing_result.data if existing_result else None
    if not isinstance(existing_patient, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    incoming_patient = payload.get("patient")
    if not isinstance(incoming_patient, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Import payload is missing patient profile section.",
        )

    patient_update_payload: dict[str, Any] = {}
    for key, value in incoming_patient.items():
        if key in IMMUTABLE_PATIENT_IMPORT_FIELDS:
            continue
        if key not in existing_patient and key not in {
            "medical_history",
            "immunization_records",
            "treatment_history",
        }:
            continue
        patient_update_payload[key] = value

    patient_update_payload = _apply_medical_history_aliases(
        patient_update_payload,
        existing_patient=existing_patient,
    )
    patient_update_payload = {
        key: value
        for key, value in patient_update_payload.items()
        if key in existing_patient
    }
    patient_update_payload = _prepare_patient_payload(patient_update_payload, partial=True)
    if patient_update_payload:
        try:
            update_result = supabase.table("patients").update(patient_update_payload).eq(
                "id", str(patient_uuid)
            ).execute()
        except Exception as exc:
            if _is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Patient import failed due to a uniqueness conflict.",
                ) from exc
            logger.exception("Failed to update patient during import patient_id=%s", patient_uuid)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update patient profile during import.",
            ) from exc

        if not update_result or not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Patient profile import update returned no data.",
            )

    _sync_linked_user_contact(
        supabase,
        linked_user_id=str(existing_patient.get("user_id")) if existing_patient.get("user_id") else None,
        patient_update_payload=patient_update_payload,
    )

    vitals_count = _replace_patient_table_rows(
        supabase,
        table_name="vital_signs",
        patient_uuid=patient_uuid,
        rows=payload.get("vitals") or [],
    )
    consultations_count = _replace_patient_table_rows(
        supabase,
        table_name="consultations",
        patient_uuid=patient_uuid,
        rows=payload.get("consultations") or [],
    )
    existing_record_paths = (
        _fetch_patient_record_storage_paths(supabase, patient_uuid=patient_uuid)
        if clear_existing_record_files
        else []
    )

    normalized_record_rows: list[dict[str, Any]] = []
    record_files_missing = 0
    record_file_path_map = record_file_path_map or {}
    for raw_row in payload.get("records") or []:
        if not isinstance(raw_row, dict):
            continue
        row = dict(raw_row)
        image_path = _coerce_nullable_text(row.get("image_path"))
        if image_path:
            mapped = record_file_path_map.get(image_path)
            if mapped:
                row["image_path"] = mapped
            elif record_file_path_map:
                row["image_path"] = None
                record_files_missing += 1
        normalized_record_rows.append(row)

    records_count = _replace_patient_table_rows(
        supabase,
        table_name="medical_records",
        patient_uuid=patient_uuid,
        rows=normalized_record_rows,
    )

    removed_files_failed = 0
    if clear_existing_record_files and existing_record_paths:
        removed_files_failed = _remove_storage_paths(supabase, existing_record_paths)

    return {
        "vitals_imported": vitals_count,
        "consultations_imported": consultations_count,
        "records_imported": records_count,
        "files_imported": len(record_file_path_map),
        "record_files_missing": record_files_missing,
        "record_files_deleted": max(0, len(existing_record_paths) - removed_files_failed),
        "record_files_delete_failed": removed_files_failed,
    }


def _build_patient_import_result(
    *,
    patient_uuid: UUID,
    import_format: str,
    summary: dict[str, int],
    warning: Optional[str] = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "success",
        "patient_id": str(patient_uuid),
        "import_format": import_format,
        "vitals_imported": summary.get("vitals_imported", 0),
        "consultations_imported": summary.get("consultations_imported", 0),
        "records_imported": summary.get("records_imported", 0),
        "files_imported": summary.get("files_imported", 0),
        "message": "Patient data imported successfully.",
    }
    if summary.get("record_files_missing", 0) > 0:
        result["warning"] = (
            f"{summary['record_files_missing']} record attachments could not be restored from ZIP."
        )
    if warning:
        if result.get("warning"):
            result["warning"] = f"{result['warning']} {warning}"
        else:
            result["warning"] = warning
    return result


async def _run_patient_import_job(
    *,
    job_id: str,
    patient_uuid: UUID,
    file_name: str,
    import_format: str,
    content: bytes,
) -> None:
    try:
        _update_patient_import_job(job_id, status="running", stage="Validating import file", progress=5)

        if import_format != "zip":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported import format: {import_format}",
            )

        _update_patient_import_job(job_id, stage="Reading ZIP archive", progress=18)
        normalized_payload, attachment_specs, archive_warning = _extract_global_import_payload_from_archive(content)
        _update_patient_import_job(
            job_id,
            stage="Parsed JSON payload from ZIP",
            progress=38,
            ocr_current_page=None,
            ocr_total_pages=None,
        )

        source_patient_id = _coerce_nullable_text(normalized_payload.get("patient_id"))

        warning_messages: list[str] = []
        if archive_warning:
            warning_messages.append(archive_warning)
        if source_patient_id and source_patient_id != str(patient_uuid):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Import file patient_id ({source_patient_id}) does not match "
                    f"target patient_id ({patient_uuid})."
                ),
            )

        supabase = get_supabase()
        _update_patient_import_job(job_id, stage="Restoring record attachments", progress=46)
        record_path_mapping = _upload_global_import_record_files(
            supabase,
            patient_uuid=patient_uuid,
            attachment_specs=attachment_specs,
        )
        _update_patient_import_job(job_id, stage="Applying imported data", progress=82)
        summary = _apply_patient_text_import(
            supabase,
            patient_uuid=patient_uuid,
            payload=normalized_payload,
            record_file_path_map=record_path_mapping,
            clear_existing_record_files=True,
        )
        result_payload = _build_patient_import_result(
            patient_uuid=patient_uuid,
            import_format=import_format,
            summary=summary,
            warning=" ".join(warning_messages).strip() if warning_messages else None,
        )

        _update_patient_import_job(
            job_id,
            status="completed",
            stage="Completed",
            progress=100,
            result=result_payload,
            error=None,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False)
        _update_patient_import_job(
            job_id,
            status="failed",
            stage="Failed",
            error=detail,
        )
    except Exception:
        logger.exception("Unhandled error during patient import job_id=%s", job_id)
        _update_patient_import_job(
            job_id,
            status="failed",
            stage="Failed",
            error="Unexpected error during patient import.",
        )


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


def _coerce_history_dict(value: Any, *, field_name: str) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"{field_name} must be an object when provided.",
    )


def _extract_history_list(source: Optional[dict[str, Any]], key: str) -> Any:
    if not isinstance(source, dict) or key not in source:
        return _HISTORY_VALUE_MISSING
    value = source.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_history_text_list(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _first_list_value(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return value
    return []


def _history_list_candidate(value: Any) -> Optional[list[Any]]:
    if value is None:
        return None
    parsed = _parse_json_like_text(value) if isinstance(value, str) else value
    if parsed is None:
        return None
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _first_history_list(*values: Any) -> list[Any]:
    for value in values:
        candidate = _history_list_candidate(value)
        if candidate is not None:
            return candidate
    return []


def _coerce_history_list(value: Any) -> list[Any]:
    candidate = _history_list_candidate(value)
    return candidate if candidate is not None else []


def _nested_history_value(source: Any, key: str) -> Any:
    if not isinstance(source, dict):
        return None
    return source.get(key)


def _medical_history_prefill_has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and not _is_null_import_text(text)
    return True


def _build_medical_history_prefill(source: dict[str, Any]) -> dict[str, list[Any]]:
    medical_history = source.get("medical_history") if isinstance(source.get("medical_history"), dict) else {}
    family_history = source.get("family_medical_history") if isinstance(source.get("family_medical_history"), dict) else {}
    immunization = source.get("immunization_records") if isinstance(source.get("immunization_records"), dict) else {}
    treatment_history = source.get("treatment_history") if isinstance(source.get("treatment_history"), dict) else {}

    fallback_medical = family_history.get("medical_history") if isinstance(family_history.get("medical_history"), dict) else {}
    fallback_immunization = (
        family_history.get("immunization_records")
        if isinstance(family_history.get("immunization_records"), dict)
        else {}
    )
    fallback_treatment = family_history.get("treatment_history") if isinstance(family_history.get("treatment_history"), dict) else {}

    return {
        "chronic_conditions": _first_history_list(
            _nested_history_value(medical_history, "chronic_conditions"),
            source.get("chronic_conditions"),
        ),
        "past_surgeries": _first_history_list(
            _nested_history_value(medical_history, "past_surgeries"),
            source.get("past_surgeries"),
            source.get("surgical_history"),
        ),
        "hospitalizations": _first_history_list(
            _nested_history_value(medical_history, "hospitalizations"),
            _nested_history_value(fallback_medical, "hospitalizations"),
            _nested_history_value(family_history, "hospitalizations"),
            source.get("hospitalizations"),
        ),
        "medications_history": _first_history_list(
            _nested_history_value(medical_history, "medications_history"),
            _nested_history_value(fallback_medical, "medications_history"),
            _nested_history_value(family_history, "medications_history"),
            source.get("medications_history"),
        ),
        "allergies": _first_history_list(
            _nested_history_value(medical_history, "allergies"),
            source.get("allergies"),
        ),
        "psychiatric_history": _first_history_list(
            _nested_history_value(medical_history, "psychiatric_history"),
            _nested_history_value(fallback_medical, "psychiatric_history"),
            _nested_history_value(family_history, "psychiatric_history"),
            source.get("psychiatric_history"),
        ),
        "family_history_of_chronic_conditions": _first_history_list(
            _nested_history_value(family_history, "family_history_of_chronic_conditions"),
            _nested_history_value(family_history, "chronic_conditions"),
            source.get("family_history_of_chronic_conditions"),
        ),
        "family_history_of_mental_health_conditions": _first_history_list(
            _nested_history_value(family_history, "family_history_of_mental_health_conditions"),
            source.get("family_history_of_mental_health_conditions"),
        ),
        "family_history_of_genetic_conditions": _first_history_list(
            _nested_history_value(family_history, "family_history_of_genetic_conditions"),
            source.get("family_history_of_genetic_conditions"),
        ),
        "vaccines_administered": _first_history_list(
            _nested_history_value(immunization, "vaccines_administered"),
            _nested_history_value(fallback_immunization, "vaccines_administered"),
            _nested_history_value(family_history, "vaccines_administered"),
            source.get("vaccines_administered"),
        ),
        "vaccines_due": _first_history_list(
            _nested_history_value(immunization, "vaccines_due"),
            _nested_history_value(fallback_immunization, "vaccines_due"),
            _nested_history_value(family_history, "vaccines_due"),
            source.get("vaccines_due"),
        ),
        "previous_treatments": _first_history_list(
            _nested_history_value(treatment_history, "previous_treatments"),
            _nested_history_value(fallback_treatment, "previous_treatments"),
            _nested_history_value(family_history, "previous_treatments"),
            source.get("previous_treatments"),
        ),
        "physiotherapy": _first_history_list(
            _nested_history_value(treatment_history, "physiotherapy"),
            _nested_history_value(fallback_treatment, "physiotherapy"),
            _nested_history_value(family_history, "physiotherapy"),
            source.get("physiotherapy"),
        ),
        "other_relevant_treatments": _first_history_list(
            _nested_history_value(treatment_history, "other_relevant_treatments"),
            _nested_history_value(fallback_treatment, "other_relevant_treatments"),
            _nested_history_value(family_history, "other_relevant_treatments"),
            source.get("other_relevant_treatments"),
        ),
    }


def _build_medical_history_section_payload(patient: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(patient)

    for key in ("medical_history", "family_medical_history", "immunization_records", "treatment_history"):
        if isinstance(hydrated.get(key), dict):
            hydrated[key] = dict(hydrated.get(key))

    _hydrate_patient_medical_history_fields(hydrated)

    medical_history = hydrated.get("medical_history") if isinstance(hydrated.get("medical_history"), dict) else {}
    family_history = (
        hydrated.get("family_medical_history")
        if isinstance(hydrated.get("family_medical_history"), dict)
        else {}
    )
    immunization = hydrated.get("immunization_records") if isinstance(hydrated.get("immunization_records"), dict) else {}
    treatment_history = hydrated.get("treatment_history") if isinstance(hydrated.get("treatment_history"), dict) else {}

    prefill = _build_medical_history_prefill(hydrated)
    return {
        "chronic_conditions": _coerce_history_list(hydrated.get("chronic_conditions")),
        "surgical_history": _coerce_history_list(hydrated.get("surgical_history")),
        "allergies": _coerce_history_list(hydrated.get("allergies")),
        "medical_history": dict(medical_history),
        "family_medical_history": dict(family_history),
        "immunization_records": dict(immunization),
        "treatment_history": dict(treatment_history),
        "prefill": prefill,
    }


def _merge_treatment_medical_history_into_patient(
    patient_payload: dict[str, Any],
    treatment_medical_history: Any,
) -> dict[str, Any]:
    if not isinstance(treatment_medical_history, dict):
        return patient_payload

    merged = dict(patient_payload)
    for key in MEDICAL_HISTORY_SECTION_PATIENT_KEYS:
        if key not in merged and key in treatment_medical_history:
            merged[key] = treatment_medical_history.get(key)

    if "chronic_conditions" not in merged and "chronic_conditions" in treatment_medical_history:
        merged["chronic_conditions"] = treatment_medical_history.get("chronic_conditions")
    if "surgical_history" not in merged:
        if "surgical_history" in treatment_medical_history:
            merged["surgical_history"] = treatment_medical_history.get("surgical_history")
        elif "past_surgeries" in treatment_medical_history:
            merged["surgical_history"] = treatment_medical_history.get("past_surgeries")
    if "allergies" not in merged and "allergies" in treatment_medical_history:
        merged["allergies"] = treatment_medical_history.get("allergies")

    medical_history = dict(merged.get("medical_history")) if isinstance(merged.get("medical_history"), dict) else {}
    if "chronic_conditions" not in medical_history and "chronic_conditions" in treatment_medical_history:
        medical_history["chronic_conditions"] = treatment_medical_history.get("chronic_conditions")
    if "past_surgeries" not in medical_history and "past_surgeries" in treatment_medical_history:
        medical_history["past_surgeries"] = treatment_medical_history.get("past_surgeries")
    if "allergies" not in medical_history and "allergies" in treatment_medical_history:
        medical_history["allergies"] = treatment_medical_history.get("allergies")
    for key in MEDICAL_HISTORY_FAMILY_FALLBACK_KEYS:
        if key not in medical_history and key in treatment_medical_history:
            medical_history[key] = treatment_medical_history.get(key)
    if medical_history:
        merged["medical_history"] = medical_history

    family_history = (
        dict(merged.get("family_medical_history"))
        if isinstance(merged.get("family_medical_history"), dict)
        else {}
    )
    for key in (
        "family_history_of_chronic_conditions",
        "family_history_of_mental_health_conditions",
        "family_history_of_genetic_conditions",
        "hospitalizations",
        "medications_history",
        "psychiatric_history",
    ):
        if key not in family_history and key in treatment_medical_history:
            family_history[key] = treatment_medical_history.get(key)
    if family_history:
        merged["family_medical_history"] = family_history

    immunization = dict(merged.get("immunization_records")) if isinstance(merged.get("immunization_records"), dict) else {}
    for key in ("vaccines_administered", "vaccines_due"):
        if key not in immunization and key in treatment_medical_history:
            immunization[key] = treatment_medical_history.get(key)
    if immunization:
        merged["immunization_records"] = immunization

    treatment_history = dict(merged.get("treatment_history")) if isinstance(merged.get("treatment_history"), dict) else {}
    for key in ("previous_treatments", "physiotherapy", "other_relevant_treatments"):
        if key not in treatment_history and key in treatment_medical_history:
            treatment_history[key] = treatment_medical_history.get(key)
    if treatment_history:
        merged["treatment_history"] = treatment_history

    return merged


def _apply_medical_history_aliases(
    update_fields: dict[str, Any],
    *,
    existing_patient: dict[str, Any],
) -> dict[str, Any]:
    if not update_fields:
        return update_fields

    has_medical_history_column = "medical_history" in existing_patient
    has_immunization_records_column = "immunization_records" in existing_patient
    has_treatment_history_column = "treatment_history" in existing_patient

    medical_history_present = "medical_history" in update_fields
    immunization_present = "immunization_records" in update_fields
    treatment_history_present = "treatment_history" in update_fields
    family_history_present = "family_medical_history" in update_fields

    medical_history = _coerce_history_dict(
        update_fields.get("medical_history"),
        field_name="medical_history",
    ) if medical_history_present else None
    immunization_records = _coerce_history_dict(
        update_fields.get("immunization_records"),
        field_name="immunization_records",
    ) if immunization_present else None
    treatment_history = _coerce_history_dict(
        update_fields.get("treatment_history"),
        field_name="treatment_history",
    ) if treatment_history_present else None

    if medical_history_present and not has_medical_history_column:
        update_fields.pop("medical_history", None)
    if immunization_present and not has_immunization_records_column:
        update_fields.pop("immunization_records", None)
    if treatment_history_present and not has_treatment_history_column:
        update_fields.pop("treatment_history", None)

    if family_history_present:
        family_medical_history = _coerce_history_dict(
            update_fields.get("family_medical_history"),
            field_name="family_medical_history",
        )
        family_payload = dict(family_medical_history or {})
    else:
        family_payload = dict(
            existing_patient.get("family_medical_history")
            if isinstance(existing_patient.get("family_medical_history"), dict)
            else {}
        )

    should_update_family_payload = family_history_present

    if medical_history_present:
        should_update_family_payload = True
        if medical_history is None:
            update_fields["chronic_conditions"] = []
            update_fields["surgical_history"] = []
            update_fields["allergies"] = []
            for key in MEDICAL_HISTORY_FAMILY_FALLBACK_KEYS:
                family_payload[key] = []
        else:
            chronic_conditions = _extract_history_list(medical_history, "chronic_conditions")
            if chronic_conditions is not _HISTORY_VALUE_MISSING:
                update_fields["chronic_conditions"] = chronic_conditions

            past_surgeries = _extract_history_list(medical_history, "past_surgeries")
            if past_surgeries is not _HISTORY_VALUE_MISSING:
                update_fields["surgical_history"] = past_surgeries

            allergies = _extract_history_list(medical_history, "allergies")
            if allergies is not _HISTORY_VALUE_MISSING:
                update_fields["allergies"] = _normalize_history_text_list(allergies)

            for key in MEDICAL_HISTORY_FAMILY_FALLBACK_KEYS:
                values = _extract_history_list(medical_history, key)
                if values is not _HISTORY_VALUE_MISSING:
                    family_payload[key] = values

    if immunization_present:
        should_update_family_payload = True
        if immunization_records is None:
            for key in IMMUNIZATION_FAMILY_FALLBACK_KEYS:
                family_payload[key] = []
        else:
            for key in IMMUNIZATION_FAMILY_FALLBACK_KEYS:
                values = _extract_history_list(immunization_records, key)
                if values is not _HISTORY_VALUE_MISSING:
                    family_payload[key] = values

    if treatment_history_present:
        should_update_family_payload = True
        if treatment_history is None:
            for key in TREATMENT_HISTORY_FAMILY_FALLBACK_KEYS:
                family_payload[key] = []
        else:
            for key in TREATMENT_HISTORY_FAMILY_FALLBACK_KEYS:
                values = _extract_history_list(treatment_history, key)
                if values is not _HISTORY_VALUE_MISSING:
                    family_payload[key] = values

    if should_update_family_payload:
        update_fields["family_medical_history"] = family_payload

    return update_fields


def _hydrate_patient_medical_history_fields(patient: dict[str, Any]) -> None:
    if not isinstance(patient, dict):
        return

    family_history = patient.get("family_medical_history")
    family_data = dict(family_history) if isinstance(family_history, dict) else {}

    legacy_medical = family_data.get("medical_history")
    legacy_medical_data = dict(legacy_medical) if isinstance(legacy_medical, dict) else {}
    legacy_immunization = family_data.get("immunization_records")
    legacy_immunization_data = dict(legacy_immunization) if isinstance(legacy_immunization, dict) else {}
    legacy_treatment = family_data.get("treatment_history")
    legacy_treatment_data = dict(legacy_treatment) if isinstance(legacy_treatment, dict) else {}

    medical_history = patient.get("medical_history")
    medical_data = dict(medical_history) if isinstance(medical_history, dict) else {}
    medical_data["chronic_conditions"] = _first_list_value(
        medical_data.get("chronic_conditions"),
        patient.get("chronic_conditions"),
    )
    medical_data["past_surgeries"] = _first_list_value(
        medical_data.get("past_surgeries"),
        patient.get("surgical_history"),
    )
    medical_data["allergies"] = _first_list_value(
        medical_data.get("allergies"),
        patient.get("allergies"),
    )
    medical_data["hospitalizations"] = _first_list_value(
        medical_data.get("hospitalizations"),
        legacy_medical_data.get("hospitalizations"),
        family_data.get("hospitalizations"),
    )
    medical_data["medications_history"] = _first_list_value(
        medical_data.get("medications_history"),
        legacy_medical_data.get("medications_history"),
        family_data.get("medications_history"),
    )
    medical_data["psychiatric_history"] = _first_list_value(
        medical_data.get("psychiatric_history"),
        legacy_medical_data.get("psychiatric_history"),
        family_data.get("psychiatric_history"),
    )
    patient["medical_history"] = medical_data

    family_data["family_history_of_chronic_conditions"] = _first_list_value(
        family_data.get("family_history_of_chronic_conditions"),
        family_data.get("chronic_conditions"),
    )
    family_data["family_history_of_mental_health_conditions"] = _first_list_value(
        family_data.get("family_history_of_mental_health_conditions"),
    )
    family_data["family_history_of_genetic_conditions"] = _first_list_value(
        family_data.get("family_history_of_genetic_conditions"),
    )
    patient["family_medical_history"] = family_data

    immunization_records = patient.get("immunization_records")
    immunization_data = dict(immunization_records) if isinstance(immunization_records, dict) else {}
    immunization_data["vaccines_administered"] = _first_list_value(
        immunization_data.get("vaccines_administered"),
        legacy_immunization_data.get("vaccines_administered"),
        family_data.get("vaccines_administered"),
    )
    immunization_data["vaccines_due"] = _first_list_value(
        immunization_data.get("vaccines_due"),
        legacy_immunization_data.get("vaccines_due"),
        family_data.get("vaccines_due"),
    )
    patient["immunization_records"] = immunization_data

    treatment_history = patient.get("treatment_history")
    treatment_data = dict(treatment_history) if isinstance(treatment_history, dict) else {}
    treatment_data["previous_treatments"] = _first_list_value(
        treatment_data.get("previous_treatments"),
        legacy_treatment_data.get("previous_treatments"),
        family_data.get("previous_treatments"),
    )
    treatment_data["physiotherapy"] = _first_list_value(
        treatment_data.get("physiotherapy"),
        legacy_treatment_data.get("physiotherapy"),
        family_data.get("physiotherapy"),
    )
    treatment_data["other_relevant_treatments"] = _first_list_value(
        treatment_data.get("other_relevant_treatments"),
        legacy_treatment_data.get("other_relevant_treatments"),
        family_data.get("other_relevant_treatments"),
    )
    patient["treatment_history"] = treatment_data


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


def _resolve_recorded_by_user_id(supabase: object, value: Any) -> Optional[str]:
    recorded_by = _coerce_nullable_text(value)
    if not recorded_by:
        return None

    try:
        UUID(recorded_by)
    except ValueError:
        logger.warning("Ignoring non-UUID recorded_by value=%s", recorded_by)
        return None

    try:
        user_result = supabase.table("users").select("id").eq("id", recorded_by).maybe_single().execute()
    except Exception:
        logger.exception("Failed to validate recorded_by user_id=%s", recorded_by)
        return None

    user_data = user_result.data if user_result else None
    if isinstance(user_data, dict):
        return recorded_by

    logger.warning("Ignoring unknown recorded_by user_id=%s", recorded_by)
    return None


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


def _humanize_export_key(key: str) -> str:
    clean = str(key or "").strip().replace("-", "_")
    if not clean:
        return ""
    tokens = [token for token in clean.split("_") if token]
    acronym_map = {
        "id": "ID",
        "bmi": "BMI",
        "bp": "BP",
        "ai": "AI",
        "ecg": "ECG",
        "ct": "CT",
        "mri": "MRI",
        "spo2": "SpO2",
    }
    words: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in acronym_map:
            words.append(acronym_map[lowered])
        else:
            words.append(lowered.capitalize())
    return " ".join(words)


def _export_language_key(value: Any) -> str:
    return "vi" if str(value or "").lower() == "vi" else "en"


def _pdf_text(export_language: Any) -> dict[str, str]:
    return PDF_TEXT_BY_LANGUAGE[_export_language_key(export_language)]


def _pdf_label_map(label_type: str, export_language: Any) -> dict[str, str]:
    language_key = _export_language_key(export_language)
    if label_type == "metadata":
        return PDF_METADATA_FIELD_LABELS_VI if language_key == "vi" else PDF_METADATA_FIELD_LABELS
    if label_type == "vital":
        return PDF_VITAL_FIELD_LABELS_VI if language_key == "vi" else PDF_VITAL_FIELD_LABELS
    if label_type == "medical_history":
        return PDF_MEDICAL_HISTORY_FIELD_LABELS
    if label_type == "patient":
        return PDF_PATIENT_FIELD_LABELS_VI if language_key == "vi" else PDF_PATIENT_FIELD_LABELS
    if label_type == "consultation":
        return PDF_CONSULTATION_FIELD_LABELS_VI if language_key == "vi" else PDF_CONSULTATION_FIELD_LABELS
    if label_type == "record":
        return PDF_RECORD_FIELD_LABELS_VI if language_key == "vi" else PDF_RECORD_FIELD_LABELS
    return {}


def _ordered_keys(source: dict[str, Any], preferred_keys: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for key in preferred_keys:
        if key in source and key not in seen:
            seen.add(key)
            ordered.append(key)
    for key in sorted(source.keys()):
        if key in seen:
            continue
        ordered.append(key)
    return ordered


def _append_pdf_field_line(
    lines: list[str],
    *,
    key: str,
    value: Any,
    label_map: Optional[dict[str, str]] = None,
    indent: int = 0,
) -> None:
    label = (label_map or {}).get(key) or _humanize_export_key(key) or key
    value_text = _as_export_text(value).strip()
    if not value_text:
        value_text = "-"
    prefix = " " * max(0, indent)
    lines.append(f"{prefix}{label}: {value_text}")


def _format_scalar_for_pdf(value: Any, export_language: str = "en") -> str:
    text_map = _pdf_text(export_language)
    if value is None:
        return "-"
    if isinstance(value, bool):
        return text_map["yes"] if value else text_map["no"]
    text = _as_export_text(value).strip()
    return text or "-"


def _medical_history_item_to_pdf_text(item: Any, export_language: str = "en") -> Optional[str]:
    if item is None:
        return None
    if isinstance(item, dict):
        heading = (
            _coerce_nullable_text(item.get("name"))
            or _coerce_nullable_text(item.get("title"))
            or _coerce_nullable_text(item.get("condition"))
            or _coerce_nullable_text(item.get("icd10_code"))
        )
        details: list[str] = []
        for key in _ordered_keys(item, MEDICAL_HISTORY_ITEM_PREFERRED_KEYS):
            if key in {"name", "title", "condition"}:
                continue
            value_text = _format_scalar_for_pdf(item.get(key), export_language)
            if value_text == "-":
                continue
            details.append(f"{_humanize_export_key(key)}: {value_text}")

        if heading and details:
            return f"{heading} ({', '.join(details)})"
        if heading:
            return heading

        fallback = _as_export_text(item).strip()
        return fallback or None

    text = _format_scalar_for_pdf(item, export_language).strip()
    return text if text and text != "-" else None


def _medical_history_values_to_pdf_text(value: Any, export_language: str = "en") -> str:
    text_map = _pdf_text(export_language)
    values = _coerce_history_list(value)
    if not values:
        return text_map["none"]

    formatted: list[str] = []
    for item in values:
        item_text = _medical_history_item_to_pdf_text(item, export_language)
        if item_text:
            formatted.append(item_text)

    return "; ".join(formatted) if formatted else text_map["none"]


def _append_pdf_structured_field(
    lines: list[str],
    *,
    label: str,
    value: Any,
    indent: int = 0,
    preferred_order: Optional[list[str]] = None,
    export_language: str = "en",
) -> None:
    text_map = _pdf_text(export_language)
    prefix = " " * max(0, indent)

    if value is None or (isinstance(value, str) and not value.strip()):
        lines.append(f"{prefix}{label}: -")
        return

    if isinstance(value, list):
        if not value:
            lines.append(f"{prefix}{label}: {text_map['none']}")
            return

        lines.append(f"{prefix}{label}:")
        for index, item in enumerate(value, start=1):
            item_prefix = " " * (indent + 2)
            if isinstance(item, dict):
                heading = (
                    _coerce_nullable_text(item.get("name"))
                    or _coerce_nullable_text(item.get("title"))
                    or _coerce_nullable_text(item.get("icd10_code"))
                    or f"{text_map['record_entry']} {index}"
                )
                lines.append(f"{item_prefix}- {heading}")
                nested_keys = _ordered_keys(item, preferred_order or [])
                for nested_key in nested_keys:
                    nested_value = item.get(nested_key)
                    nested_label = _humanize_export_key(nested_key)
                    _append_pdf_structured_field(
                        lines,
                        label=nested_label,
                        value=nested_value,
                        indent=indent + 6,
                        export_language=export_language,
                    )
            else:
                lines.append(f"{item_prefix}- {_format_scalar_for_pdf(item, export_language)}")
        return

    if isinstance(value, dict):
        if not value:
            lines.append(f"{prefix}{label}: {text_map['none']}")
            return
        lines.append(f"{prefix}{label}:")
        nested_keys = _ordered_keys(value, preferred_order or [])
        for nested_key in nested_keys:
            nested_value = value.get(nested_key)
            nested_label = _humanize_export_key(nested_key)
            _append_pdf_structured_field(
                lines,
                label=nested_label,
                value=nested_value,
                indent=indent + 2,
                export_language=export_language,
            )
        return

    lines.append(f"{prefix}{label}: {_format_scalar_for_pdf(value, export_language)}")


def _resolve_alias_key(raw_key: str, aliases: dict[str, str], *, threshold: float = 0.78) -> Optional[str]:
    if not raw_key:
        return None
    if raw_key in aliases:
        return aliases[raw_key]

    best_key: Optional[str] = None
    best_score = 0.0
    for candidate in aliases.keys():
        score = SequenceMatcher(None, raw_key, candidate).ratio()
        if score > best_score:
            best_score = score
            best_key = candidate

    if best_key and best_score >= threshold:
        return aliases[best_key]
    return None


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


def _is_test_result_record_type(record_type: Any) -> bool:
    return str(record_type or "").strip().lower() in TEST_RESULT_RECORD_TYPES


def _filter_test_result_records(records: list[dict]) -> list[dict]:
    return [record for record in records if _is_test_result_record_type(record.get("record_type"))]


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
    _hydrate_patient_medical_history_fields(patient_data)

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

    test_result_records = _filter_test_result_records(records)
    medical_history_section = _build_medical_history_section_payload(patient_data)

    return {
        "schema_version": 2,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "patient_id": str(patient_uuid),
        "patient": patient_data,
        "vitals": vitals_result.data or [],
        "consultations": consultations_result.data or [],
        "records": records,
        "treatment_records": {
            "regular_checkups": vitals_result.data or [],
            "medical_test_results": test_result_records,
            "medical_history": medical_history_section,
        },
    }


def _build_patient_global_export_archive(
    supabase: object,
    *,
    patient_uuid: UUID,
    export_format: PatientTextExportFormat,
    export_language: ExportLanguage = ExportLanguage.en,
) -> tuple[bytes, str]:
    payload = _build_patient_export_payload(supabase, patient_uuid)
    patient = payload.get("patient") if isinstance(payload.get("patient"), dict) else {}
    base_name = _build_patient_export_basename(patient, patient_uuid)

    json_text_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=_json_default,
    ).encode("utf-8")
    json_text_path = "text/patient_data.json"

    pdf_text_path = "text/patient_data.pdf"
    pdf_text_bytes: Optional[bytes] = None
    if export_format == PatientTextExportFormat.pdf:
        pdf_text_bytes = _render_text_pdf(_patient_payload_to_pdf_lines(payload, export_language.value))

    zip_buffer = io.BytesIO()
    used_file_names: set[str] = set()
    exported_files_manifest: list[dict[str, Any]] = []
    exported_file_count = 0

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(json_text_path, json_text_bytes)
        if pdf_text_bytes is not None:
            archive.writestr(pdf_text_path, pdf_text_bytes)

        records = payload.get("records") if isinstance(payload.get("records"), list) else []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                continue
            storage_path = _coerce_nullable_text(record.get("image_path"))
            if not storage_path:
                continue

            try:
                file_bytes = supabase.storage.from_(settings.patient_photo_bucket).download(storage_path)
            except Exception:
                logger.exception(
                    "Failed to include attachment in global export patient_id=%s record_id=%s path=%s",
                    patient_uuid,
                    record.get("id"),
                    storage_path,
                )
                continue

            if not file_bytes:
                continue

            extension = Path(storage_path).suffix
            leaf_name = _ensure_file_extension(
                _safe_filename_component(record.get("title"), f"record_{index}"),
                extension,
            )
            leaf_name = _unique_zip_name(leaf_name, used_file_names)
            archive_entry = f"files/{leaf_name}"
            archive.writestr(archive_entry, file_bytes)
            exported_file_count += 1

            exported_files_manifest.append(
                {
                    "record_id": str(record.get("id")) if record.get("id") is not None else None,
                    "record_type": record.get("record_type"),
                    "title": record.get("title"),
                    "original_image_path": storage_path,
                    "archive_file": archive_entry,
                }
            )

        manifest = {
            "schema_version": 1,
            "data_type": "patient_global_export",
            "patient_id": str(patient_uuid),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "text_format": export_format.value,
            "text_language": export_language.value,
            "display_text_file": pdf_text_path if pdf_text_bytes is not None else json_text_path,
            # Global import intentionally reads JSON text for lossless restore.
            "import_text_file": json_text_path,
            "files_exported": exported_file_count,
            "records": exported_files_manifest,
        }
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default),
        )

    filename = f"{base_name}.zip"
    return zip_buffer.getvalue(), filename


def _extract_global_import_payload_from_archive(content: bytes) -> tuple[dict[str, Any], list[dict[str, Any]], Optional[str]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid ZIP file for global import.",
        ) from exc

    warning: Optional[str] = None

    with archive:
        archive_entries = [name for name in archive.namelist() if name and not name.endswith("/")]
        if not archive_entries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Import ZIP is empty.",
            )

        manifest_data: dict[str, Any] = {}
        if "manifest.json" in archive_entries:
            try:
                manifest_raw = archive.read("manifest.json")
                manifest_candidate = _parse_patient_import_json_payload(manifest_raw)
                if isinstance(manifest_candidate, dict):
                    manifest_data = manifest_candidate
            except Exception:
                warning = "manifest.json could not be parsed. Falling back to best-effort ZIP parsing."

        text_json_entry = _coerce_nullable_text(manifest_data.get("import_text_file"))
        if text_json_entry not in archive_entries:
            text_json_entry = None

        if not text_json_entry:
            for candidate in archive_entries:
                normalized = candidate.lower()
                if not normalized.endswith(".json"):
                    continue
                if normalized == "manifest.json":
                    continue
                text_json_entry = candidate
                break

        if not text_json_entry:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Import ZIP is missing a JSON text payload.",
            )

        raw_payload = _parse_patient_import_json_payload(archive.read(text_json_entry))
        normalized_payload = _normalize_patient_import_payload(raw_payload)

        attachment_specs: list[dict[str, Any]] = []
        records_manifest = manifest_data.get("records")
        if isinstance(records_manifest, list):
            for item in records_manifest:
                if not isinstance(item, dict):
                    continue
                old_path = _coerce_nullable_text(item.get("original_image_path"))
                archive_file = _coerce_nullable_text(item.get("archive_file"))
                if not old_path or not archive_file:
                    continue
                if archive_file not in archive_entries:
                    continue
                try:
                    attachment_bytes = archive.read(archive_file)
                except Exception:
                    continue
                if not attachment_bytes:
                    continue
                extension = Path(archive_file).suffix or Path(old_path).suffix
                attachment_specs.append(
                    {
                        "old_path": old_path,
                        "extension": extension,
                        "content_type": _guess_content_type(extension or ""),
                        "bytes": attachment_bytes,
                    }
                )

        if not attachment_specs:
            file_entries = sorted(
                [
                    name for name in archive_entries
                    if name.lower().startswith("files/")
                ]
            )
            old_paths = [
                _coerce_nullable_text(record.get("image_path"))
                for record in (normalized_payload.get("records") or [])
                if isinstance(record, dict)
            ]
            old_paths = [path for path in old_paths if path]

            for old_path, archive_file in zip(old_paths, file_entries):
                try:
                    attachment_bytes = archive.read(archive_file)
                except Exception:
                    continue
                if not attachment_bytes:
                    continue
                extension = Path(archive_file).suffix or Path(str(old_path)).suffix
                attachment_specs.append(
                    {
                        "old_path": old_path,
                        "extension": extension,
                        "content_type": _guess_content_type(extension or ""),
                        "bytes": attachment_bytes,
                    }
                )

            if file_entries and old_paths and len(file_entries) != len(old_paths):
                warning = (
                    "Global import used fallback file matching by order; some attachments may require manual review."
                )

    return normalized_payload, attachment_specs, warning


def _upload_global_import_record_files(
    supabase: object,
    *,
    patient_uuid: UUID,
    attachment_specs: list[dict[str, Any]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    bucket = settings.patient_photo_bucket

    for item in attachment_specs:
        old_path = _coerce_nullable_text(item.get("old_path"))
        if not old_path:
            continue
        extension = str(item.get("extension") or "").strip()
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        content_type = str(item.get("content_type") or _guess_content_type(extension))
        file_bytes = item.get("bytes")
        if not isinstance(file_bytes, (bytes, bytearray)):
            continue

        new_storage_path = f"records/{patient_uuid}/{uuid4()}{extension}"
        try:
            upload_result = supabase.storage.from_(bucket).upload(
                new_storage_path,
                bytes(file_bytes),
                file_options={
                    "content-type": content_type,
                    "upsert": "true",
                },
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload imported record file for path: {old_path}",
            ) from exc

        if isinstance(upload_result, dict) and upload_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload imported record file for path: {old_path}",
            )

        mapping[old_path] = new_storage_path

    return mapping


def _patient_payload_to_pdf_lines(payload: dict[str, Any], export_language: str = "en") -> list[str]:
    text_map = _pdf_text(export_language)
    patient_label_map = _pdf_label_map("patient", export_language)
    vital_label_map = _pdf_label_map("vital", export_language)
    consultation_label_map = _pdf_label_map("consultation", export_language)
    record_label_map = _pdf_label_map("record", export_language)
    report_title = text_map["patient_record_export"]
    lines: list[str] = [
        report_title,
        "=" * max(36, min(72, len(report_title))),
        f"{text_map['patient_id']}: {payload.get('patient_id', '')}",
        f"{text_map['exported_at']}: {payload.get('exported_at', '')}",
        "",
    ]

    vitals = payload.get("vitals") if isinstance(payload.get("vitals"), list) else []
    consultations = payload.get("consultations") if isinstance(payload.get("consultations"), list) else []
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    patient = payload.get("patient") if isinstance(payload.get("patient"), dict) else {}
    treatment_records = payload.get("treatment_records") if isinstance(payload.get("treatment_records"), dict) else {}
    medical_history_label_map = _pdf_label_map("medical_history", export_language)
    regular_checkups = (
        treatment_records.get("regular_checkups")
        if isinstance(treatment_records.get("regular_checkups"), list)
        else vitals
    )
    medical_test_results = (
        treatment_records.get("medical_test_results")
        if isinstance(treatment_records.get("medical_test_results"), list)
        else _filter_test_result_records(records)
    )
    medical_history_section = (
        treatment_records.get("medical_history")
        if isinstance(treatment_records.get("medical_history"), dict)
        else _build_medical_history_section_payload(patient)
    )
    medical_history_prefill = _coerce_medical_history_prefill_map(medical_history_section.get("prefill"))
    if not any(_medical_history_prefill_has_value(medical_history_prefill.get(key)) for key in MEDICAL_HISTORY_PREFILL_KEYS):
        medical_history_prefill = _build_medical_history_prefill(medical_history_section)
    medical_history_populated_fields = sum(
        1
        for key in MEDICAL_HISTORY_PREFILL_KEYS
        if _medical_history_prefill_has_value(medical_history_prefill.get(key))
    )
    treatment_record_count = (
        len(regular_checkups)
        + len(medical_test_results)
        + (1 if medical_history_populated_fields > 0 else 0)
    )

    lines.extend(
        [
            text_map["summary"],
            f"{text_map.get('treatment_records', 'Treatment Records')}: {treatment_record_count}",
            f"{text_map['vital_signs']}: {len(regular_checkups)}",
            f"{text_map['consultations']}: {len(consultations)}",
            f"{text_map['medical_records']}: {len(medical_test_results)}",
            f"{text_map.get('medical_history', 'Medical History')}: {medical_history_populated_fields}",
            "",
            f"1. {text_map['patient_profile']}",
        ]
    )

    if patient:
        group_definitions: list[tuple[str, list[str]]] = [
            (
                text_map["demographics"],
                ["full_name", "date_of_birth", "gender", "blood_type", "national_id"],
            ),
            (
                text_map["contact_information"],
                [
                    "phone_primary",
                    "phone_secondary",
                    "email",
                    "address_street",
                    "address_ward",
                    "address_district",
                    "address_province",
                ],
            ),
            (
                text_map["emergency_contact"],
                [
                    "emergency_contact_name",
                    "emergency_contact_phone",
                    "emergency_contact_relationship",
                ],
            ),
            (
                text_map["clinical_status"],
                [
                    "primary_diagnosis",
                    "diagnosis_date",
                    "disease_stage",
                    "triage_priority",
                    "profile_status",
                    "last_checkup_date",
                    "next_appointment_date",
                ],
            ),
            (
                text_map["lifestyle_and_risk"],
                [
                    "smoking_status",
                    "alcohol_consumption",
                    "height_cm",
                    "weight_kg",
                    "bmi",
                ],
            ),
            (
                text_map["insurance"],
                [
                    "insurance_provider",
                    "insurance_number",
                    "insurance_expiry",
                ],
            ),
            (
                text_map["medical_background"],
                [
                    "chronic_conditions",
                    "current_medications",
                    "allergies",
                    "surgical_history",
                    "family_medical_history",
                    "medical_history",
                    "immunization_records",
                    "treatment_history",
                ],
            ),
        ]

        consumed: set[str] = set()
        for section_title, keys in group_definitions:
            section_keys = [key for key in keys if key in patient]
            if not section_keys:
                continue
            lines.append(section_title)
            for key in section_keys:
                consumed.add(key)
                label = patient_label_map.get(key) or _humanize_export_key(key)
                preferred_nested = None
                if key == "chronic_conditions":
                    preferred_nested = ["name", "icd10_code", "diagnosed_date", "stage", "notes"]
                elif key == "current_medications":
                    preferred_nested = ["name", "dosage", "frequency", "timing", "prescriber", "start_date"]
                _append_pdf_structured_field(
                    lines,
                    label=label,
                    value=patient.get(key),
                    indent=2,
                    preferred_order=preferred_nested,
                    export_language=export_language,
                )
            lines.append("")

        remaining = [key for key in sorted(patient.keys()) if key not in consumed]
        if remaining:
            lines.append(text_map["additional_profile_data"])
            for key in remaining:
                _append_pdf_structured_field(
                    lines,
                    label=patient_label_map.get(key) or _humanize_export_key(key),
                    value=patient.get(key),
                    indent=2,
                    export_language=export_language,
                )
            lines.append("")
    else:
        lines.append(text_map["no_patient_profile_data"])

    lines.append("")
    lines.append(f"2. {text_map.get('treatment_records', 'Treatment Records')}")
    lines.append("2.1 Regular Checkups")
    lines.append(f"{text_map['vital_signs']} ({len(regular_checkups)})")
    if not regular_checkups:
        lines.append(text_map["no_vital_signs_data"])
    for index, vital in enumerate(regular_checkups, start=1):
        lines.append(f"{text_map['vital_entry']} #{index}")
        if isinstance(vital, dict):
            for key in _ordered_keys(vital, PDF_VITAL_PREFERRED_ORDER):
                _append_pdf_structured_field(
                    lines,
                    label=vital_label_map.get(key) or _humanize_export_key(key),
                    value=vital.get(key),
                    indent=4,
                    export_language=export_language,
                )
        else:
            lines.append(f"  {_as_export_text(vital)}")
        lines.append("")

    lines.append("")
    lines.append("2.2 Medical Test Results")
    lines.append(f"{text_map['medical_records']} ({len(medical_test_results)})")
    if not medical_test_results:
        lines.append(text_map["no_medical_records_data"])
    for index, record in enumerate(medical_test_results, start=1):
        lines.append(f"{text_map['record_entry']} #{index}")
        if isinstance(record, dict):
            for key in _ordered_keys(record, ["record_type", "title", "created_at", "doctor_comment", "content_text", "analysis_result", "image_path", "file_extension"]):
                nested_order = None
                if key == "analysis_result":
                    nested_order = [
                        "status",
                        "summary",
                        "key_findings",
                        "clinical_significance",
                        "recommended_follow_up",
                        "urgency",
                        "confidence",
                        "limitations",
                        "model",
                        "generated_at",
                    ]
                _append_pdf_structured_field(
                    lines,
                    label=record_label_map.get(key) or _humanize_export_key(key),
                    value=record.get(key),
                    indent=4,
                    preferred_order=nested_order,
                    export_language=export_language,
                )
        else:
            lines.append(f"  {_as_export_text(record)}")
        lines.append("")

    lines.append("")
    lines.append("2.3 Medical History")
    lines.append(f"{text_map.get('medical_history', 'Medical History')} ({medical_history_populated_fields})")
    if medical_history_populated_fields == 0:
        lines.append(text_map.get("no_medical_history_data", "No medical history data."))
    else:
        for section_title, keys in MEDICAL_HISTORY_PDF_GROUPS:
            populated_keys = [
                key for key in keys
                if _medical_history_prefill_has_value(medical_history_prefill.get(key))
            ]
            if not populated_keys:
                continue
            lines.append(f"    {section_title}")
            for key in populated_keys:
                _append_pdf_field_line(
                    lines,
                    key=key,
                    value=_medical_history_values_to_pdf_text(medical_history_prefill.get(key), export_language),
                    label_map=medical_history_label_map,
                    indent=6,
                )
        lines.append("")

    lines.append("")
    lines.append(f"3. {text_map['consultations']}")
    lines.append(f"{text_map['consultations']} ({len(consultations)})")
    if not consultations:
        lines.append(text_map["no_consultations_data"])
    for index, consultation in enumerate(consultations, start=1):
        lines.append(f"{text_map['consultation_entry']} #{index}")
        if isinstance(consultation, dict):
            for key in _ordered_keys(consultation, ["started_at", "status", "priority", "chief_complaint", "summary"]):
                _append_pdf_structured_field(
                    lines,
                    label=consultation_label_map.get(key) or _humanize_export_key(key),
                    value=consultation.get(key),
                    indent=4,
                    export_language=export_language,
                )
        else:
            lines.append(f"  {_as_export_text(consultation)}")
        lines.append("")

    return lines


def _escape_pdf_text(value: str) -> str:
    # Legacy fallback path only. Single-byte font encoding will replace unsupported glyphs.
    clean = value.replace("\r", " ").replace("\n", " ")
    escaped = clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped


def _render_text_pdf_legacy(lines: list[str]) -> bytes:
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


def _load_pdf_font(font_size: int):
    from PIL import ImageFont

    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]

    for path in font_candidates:
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size=font_size)
        except Exception:
            continue

    for font_name in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size=font_size)
        except Exception:
            continue

    return ImageFont.load_default()


def _measure_text_width(draw: object, text: str, font: object) -> float:
    text_str = str(text or "")
    try:
        return float(draw.textlength(text_str, font=font))  # type: ignore[attr-defined]
    except Exception:
        try:
            bbox = draw.textbbox((0, 0), text_str, font=font)  # type: ignore[attr-defined]
            return float(max(0, bbox[2] - bbox[0]))
        except Exception:
            return float(len(text_str) * 8)


def _wrap_pdf_line(line: str, max_width: float, draw: object, font: object) -> list[str]:
    normalized = str(line or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    if not normalized:
        return [""]

    wrapped: list[str] = []
    current = ""

    for word in normalized.split(" "):
        candidate = word if not current else f"{current} {word}"
        if _measure_text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue

        if current:
            wrapped.append(current)
            current = ""

        if _measure_text_width(draw, word, font) <= max_width:
            current = word
            continue

        chunk = ""
        for char in word:
            chunk_candidate = f"{chunk}{char}"
            if _measure_text_width(draw, chunk_candidate, font) <= max_width:
                chunk = chunk_candidate
            else:
                if chunk:
                    wrapped.append(chunk)
                chunk = char
        if chunk:
            current = chunk

    if current:
        wrapped.append(current)

    return wrapped or [""]


def _render_text_pdf(lines: list[str]) -> bytes:
    """
    Render UTF-8 capable text PDF using Pillow with Unicode fonts.
    Falls back to legacy single-byte PDF renderer if Pillow rendering fails.
    """
    try:
        from PIL import Image, ImageDraw

        dpi = 150
        page_width = 1240  # A4 width at 150 DPI
        page_height = 1754  # A4 height at 150 DPI
        margin_left = 72
        margin_right = 72
        margin_top = 80
        margin_bottom = 80
        font_size = 24

        font = _load_pdf_font(font_size)
        measure_canvas = Image.new("RGB", (8, 8), "white")
        measure_draw = ImageDraw.Draw(measure_canvas)
        try:
            bbox = measure_draw.textbbox((0, 0), "Ag", font=font)
            line_height = max(28, (bbox[3] - bbox[1]) + 10)
        except Exception:
            line_height = 34

        max_text_width = float(page_width - margin_left - margin_right)
        max_lines_per_page = max(1, (page_height - margin_top - margin_bottom) // line_height)

        wrapped_lines: list[str] = []
        for line in lines:
            wrapped_lines.extend(_wrap_pdf_line(str(line or ""), max_text_width, measure_draw, font))

        pages: list[object] = []
        for offset in range(0, len(wrapped_lines), max_lines_per_page):
            page_lines = wrapped_lines[offset:offset + max_lines_per_page]
            image = Image.new("RGB", (page_width, page_height), "white")
            draw = ImageDraw.Draw(image)
            y = margin_top
            for text_line in page_lines:
                draw.text((margin_left, y), text_line, fill=(0, 0, 0), font=font)
                y += line_height
            pages.append(image)

        if not pages:
            image = Image.new("RGB", (page_width, page_height), "white")
            pages.append(image)

        output = io.BytesIO()
        first_page = pages[0]
        remaining_pages = pages[1:]
        first_page.save(
            output,
            format="PDF",
            resolution=float(dpi),
            save_all=True,
            append_images=remaining_pages,
        )

        for page in pages:
            try:
                page.close()
            except Exception:
                continue

        return output.getvalue()
    except Exception:
        logger.exception("Unicode PDF rendering failed; using legacy PDF renderer.")
        return _render_text_pdf_legacy(lines)


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
        "id, full_name, date_of_birth, gender, national_id, insurance_number, phone_primary, email, "
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
    _hydrate_patient_medical_history_fields(patient_data)

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
        _hydrate_patient_medical_history_fields(patient_data)

    return {
        "patient": patient_data,
        "recent_vitals": vitals.data or [],
        "recent_consultations": consultations.data or [],
    }


@router.get("/patients/{patient_id}/summary")
async def get_patient_summary(patient_id: str):
    """
    Generate an AI clinical summary for the patient profile.

    Uses MedGemma to synthesize the patient's medical data into a structured
    clinical overview following the Problem List / POMR medical format.

    Returns:
        JSON with summary text, generation timestamp, and model name.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    # Verify patient exists
    supabase = get_supabase()
    patient = supabase.table("patients").select("id").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()

    if not patient or not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await generate_patient_profile_summary(patient_uuid)
    return result


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

    update_fields = _apply_medical_history_aliases(
        update_fields,
        existing_patient=existing_patient,
    )
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
    _hydrate_patient_medical_history_fields(patient_data)

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


@router.post("/patient-metadata/export")
async def export_patient_metadata(
    request: PatientMetadataExportRequest,
    export_format: PatientTextExportFormat = Query(
        default=PatientTextExportFormat.json,
        alias="format",
        description="Export format for patient metadata (json or pdf).",
    ),
    export_language: ExportLanguage = Query(
        default=ExportLanguage.en,
        alias="lang",
        description="Export language for PDF rendering (vi or en).",
    ),
):
    normalized_metadata = _normalize_patient_metadata_payload(request.metadata or {})

    payload = {
        "schema_version": 1,
        "data_type": "patient_metadata",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "metadata": normalized_metadata,
    }

    base_name = "patient-metadata"
    full_name = _coerce_nullable_text(normalized_metadata.get("full_name"))
    if full_name:
        base_name = _safe_slug(full_name, "patient-metadata") + "-metadata"

    if export_format == PatientTextExportFormat.json:
        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8")
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.json"'},
        )

    pdf_bytes = _render_text_pdf(_patient_metadata_payload_to_pdf_lines(normalized_metadata, export_language.value))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
    )


@router.post("/patient-metadata/import/preview")
async def import_patient_metadata_preview(file: UploadFile = File(...)):
    file_name = file.filename or "import"
    logger.warning(
        "[metadata-import-preview] start file=%s content_type=%s",
        file_name,
        file.content_type,
    )

    try:
        extension = Path(file_name).suffix.lower()
        if extension not in SUBDATA_IMPORT_ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported import file type. Allowed: .json, .pdf",
            )

        content = await file.read()
        logger.warning("[metadata-import-preview] file_bytes=%s extension=%s", len(content), extension)
        if not content:
            raise HTTPException(status_code=400, detail="Import file is empty")

        if extension == ".json":
            metadata = _parse_patient_metadata_json_payload(content)
        else:
            temp_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(content)
                    temp_path = tmp.name
                logger.warning("[metadata-import-preview] running OCR path=%s", temp_path)
                metadata_pdf_max_pages = max(
                    1,
                    min(
                        settings.import_pdf_ocr_max_pages,
                        settings.import_metadata_pdf_ocr_max_pages,
                    ),
                )
                raw_text = await extract_text(
                    temp_path,
                    file_type="pdf",
                    pdf_dpi=max(72, settings.import_pdf_ocr_dpi),
                    pdf_max_pages=metadata_pdf_max_pages,
                    pdf_preprocess=settings.import_pdf_ocr_preprocess,
                    pdf_render_threads=max(1, int(settings.import_pdf_render_threads)),
                )
                _log_ocr_debug_dump("metadata-import-preview", raw_text)
            finally:
                if temp_path:
                    try:
                        Path(temp_path).unlink(missing_ok=True)
                    except Exception:
                        logger.warning("Failed to remove temporary metadata import file path=%s", temp_path)

            metadata = _parse_patient_metadata_pdf_payload(raw_text or "")

        logger.warning(
            "[metadata-import-preview] success parsed_fields=%s keys=%s",
            len(metadata),
            sorted(metadata.keys()),
        )
        return {
            "status": "success",
            "metadata": metadata,
            "message": "Patient metadata import preview generated.",
        }
    except OCRDependencyError as exc:
        detail = str(exc)
        logger.warning("[metadata-import-preview] ocr dependency error detail=%s", detail, exc_info=True)
        raise HTTPException(status_code=503, detail=detail) from exc
    except HTTPException as exc:
        logger.warning("[metadata-import-preview] failed detail=%s", exc.detail, exc_info=True)
        raise
    except Exception:
        logger.exception("[metadata-import-preview] unexpected error")
        raise


@router.get("/patients/{patient_id}/medical-history/export")
async def export_patient_medical_history(
    patient_id: str,
    export_format: PatientTextExportFormat = Query(
        default=PatientTextExportFormat.json,
        alias="format",
        description="Export format for medical-history section (json or pdf).",
    ),
    export_language: ExportLanguage = Query(
        default=ExportLanguage.en,
        alias="lang",
        description="Export language for PDF rendering (vi or en).",
    ),
):
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    patient_result = supabase.table("patients").select("*").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    patient_data = patient_result.data if patient_result else None
    if not isinstance(patient_data, dict):
        raise HTTPException(status_code=404, detail="Patient not found")

    _hydrate_patient_medical_history_fields(patient_data)
    medical_history_section = _build_medical_history_section_payload(patient_data)
    payload = {
        "schema_version": 1,
        "data_type": "medical_history",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "patient_id": str(patient_uuid),
        "medical_history_section": medical_history_section,
    }

    patient_slug = _safe_slug(patient_data.get("full_name"), "patient")
    base_name = f"{patient_slug}-{patient_uuid}-medical-history"

    if export_format == PatientTextExportFormat.json:
        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8")
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.json"'},
        )

    pdf_bytes = _render_text_pdf(_medical_history_export_payload_to_pdf_lines(payload, export_language.value))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
    )


@router.post("/patients/{patient_id}/medical-history/import/preview")
async def import_patient_medical_history_preview(
    patient_id: str,
    file: UploadFile = File(...),
):
    file_name = file.filename or "import"
    logger.warning(
        "[medical-history-import-preview] start patient_id=%s file=%s content_type=%s",
        patient_id,
        file_name,
        file.content_type,
    )

    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    patient_result = supabase.table("patients").select("id").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    if not patient_result or not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        extension = Path(file_name).suffix.lower()
        if extension not in SUBDATA_IMPORT_ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported import file type. Allowed: .json, .pdf",
            )

        content = await file.read()
        logger.warning(
            "[medical-history-import-preview] patient_id=%s file_bytes=%s extension=%s",
            patient_id,
            len(content),
            extension,
        )
        if not content:
            raise HTTPException(status_code=400, detail="Import file is empty")

        if extension == ".json":
            prefill = _parse_medical_history_import_json_payload(content)
        else:
            temp_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(content)
                    temp_path = tmp.name
                logger.warning("[medical-history-import-preview] running OCR path=%s", temp_path)
                raw_text = await extract_text(
                    temp_path,
                    file_type="pdf",
                    pdf_dpi=max(72, settings.import_pdf_ocr_dpi),
                    pdf_max_pages=settings.import_pdf_ocr_max_pages,
                    pdf_preprocess=settings.import_pdf_ocr_preprocess,
                    pdf_render_threads=max(1, int(settings.import_pdf_render_threads)),
                )
                _log_ocr_debug_dump("medical-history-import-preview", raw_text)
            finally:
                if temp_path:
                    try:
                        Path(temp_path).unlink(missing_ok=True)
                    except Exception:
                        logger.warning(
                            "Failed to remove temporary medical-history import file path=%s",
                            temp_path,
                        )

            prefill = _parse_medical_history_import_pdf_payload(raw_text or "")
    except OCRDependencyError as exc:
        detail = str(exc)
        logger.warning(
            "[medical-history-import-preview] ocr dependency error patient_id=%s detail=%s",
            patient_id,
            detail,
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail=detail) from exc
    except HTTPException as exc:
        logger.warning(
            "[medical-history-import-preview] failed patient_id=%s detail=%s",
            patient_id,
            exc.detail,
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("[medical-history-import-preview] unexpected error patient_id=%s", patient_id)
        raise

    logger.warning(
        "[medical-history-import-preview] success patient_id=%s populated_fields=%s",
        patient_id,
        sum(1 for key in MEDICAL_HISTORY_PREFILL_KEYS if _medical_history_prefill_has_value(prefill.get(key))),
    )
    return {
        "status": "success",
        "patient_id": str(patient_uuid),
        "prefill": prefill,
        "message": "Medical-history import preview generated.",
    }


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

    recorded_by = _resolve_recorded_by_user_id(supabase, data.get("recorded_by"))
    if recorded_by:
        data["recorded_by"] = recorded_by
    else:
        data.pop("recorded_by", None)

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


@router.put("/patients/{patient_id}/vitals/{vital_id}")
async def update_patient_vital(
    patient_id: str,
    vital_id: str,
    request: VitalSignCreateRequest,
):
    """
    Update an existing vital sign entry for a patient.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    try:
        vital_uuid = UUID(vital_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vital_id format")

    supabase = get_supabase()

    existing = (
        supabase.table("vital_signs")
        .select("id, patient_id")
        .eq("id", str(vital_uuid))
        .eq("patient_id", str(patient_uuid))
        .maybe_single()
        .execute()
    )
    if not existing or not existing.data:
        raise HTTPException(status_code=404, detail="Vital sign entry not found")

    data = request.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if isinstance(data.get("source"), VitalSource):
        data["source"] = data["source"].value
    if isinstance(data.get("blood_glucose_timing"), GlucoseTiming):
        data["blood_glucose_timing"] = data["blood_glucose_timing"].value
    if isinstance(data.get("recorded_at"), datetime):
        data["recorded_at"] = data["recorded_at"].isoformat()

    if "recorded_by" in data:
        recorded_by = _resolve_recorded_by_user_id(supabase, data.get("recorded_by"))
        if recorded_by:
            data["recorded_by"] = recorded_by
        else:
            data.pop("recorded_by", None)

    result = (
        supabase.table("vital_signs")
        .update(data)
        .eq("id", str(vital_uuid))
        .eq("patient_id", str(patient_uuid))
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to update vital sign entry",
        )

    return {
        "status": "success",
        "vital": result.data[0],
    }


@router.delete("/patients/{patient_id}/vitals/{vital_id}")
async def delete_patient_vital(
    patient_id: str,
    vital_id: str,
):
    """
    Delete a vital sign entry for a patient.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    try:
        vital_uuid = UUID(vital_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vital_id format")

    supabase = get_supabase()
    result = (
        supabase.table("vital_signs")
        .delete()
        .eq("id", str(vital_uuid))
        .eq("patient_id", str(patient_uuid))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Vital sign entry not found")

    return {
        "status": "success",
        "patient_id": str(patient_uuid),
        "vital_id": str(vital_uuid),
        "message": "Vital sign entry deleted.",
    }


@router.get("/patients/{patient_id}/vitals/export")
async def export_patient_vitals(
    patient_id: str,
    export_format: PatientTextExportFormat = Query(
        default=PatientTextExportFormat.json,
        alias="format",
        description="Export format for vital-sign data (json or pdf).",
    ),
    export_language: ExportLanguage = Query(
        default=ExportLanguage.en,
        alias="lang",
        description="Export language for PDF rendering (vi or en).",
    ),
):
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

    vitals_result = supabase.table("vital_signs").select("*").eq(
        "patient_id", str(patient_uuid)
    ).order("recorded_at", desc=True).execute()

    payload = {
        "schema_version": 1,
        "data_type": "vital_signs",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "patient_id": str(patient_uuid),
        "vitals": vitals_result.data or [],
    }

    patient_slug = _safe_slug(patient_data.get("full_name"), "patient")
    base_name = f"{patient_slug}-{patient_uuid}-vitals"

    if export_format == PatientTextExportFormat.json:
        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ).encode("utf-8")
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.json"'},
        )

    pdf_bytes = _render_text_pdf(_vital_export_payload_to_pdf_lines(payload, export_language.value))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
    )


@router.post("/patients/{patient_id}/vitals/import/preview")
async def import_patient_vitals_preview(
    patient_id: str,
    file: UploadFile = File(...),
):
    file_name = file.filename or "import"
    logger.warning(
        "[vital-import-preview] start patient_id=%s file=%s content_type=%s",
        patient_id,
        file_name,
        file.content_type,
    )

    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    patient_result = supabase.table("patients").select("id").eq(
        "id", str(patient_uuid)
    ).maybe_single().execute()
    if not patient_result or not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        extension = Path(file_name).suffix.lower()
        if extension not in SUBDATA_IMPORT_ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported import file type. Allowed: .json, .pdf",
            )

        content = await file.read()
        logger.warning(
            "[vital-import-preview] patient_id=%s file_bytes=%s extension=%s",
            patient_id,
            len(content),
            extension,
        )
        if not content:
            raise HTTPException(status_code=400, detail="Import file is empty")

        if extension == ".json":
            rows = _parse_vital_import_json_payload(content)
        else:
            temp_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(content)
                    temp_path = tmp.name
                logger.warning("[vital-import-preview] running OCR path=%s", temp_path)
                raw_text = await extract_text(
                    temp_path,
                    file_type="pdf",
                    pdf_dpi=max(72, settings.import_pdf_ocr_dpi),
                    pdf_max_pages=settings.import_pdf_ocr_max_pages,
                    pdf_preprocess=settings.import_pdf_ocr_preprocess,
                    pdf_render_threads=max(1, int(settings.import_pdf_render_threads)),
                )
                _log_ocr_debug_dump("vital-import-preview", raw_text)
            finally:
                if temp_path:
                    try:
                        Path(temp_path).unlink(missing_ok=True)
                    except Exception:
                        logger.warning("Failed to remove temporary vital import file path=%s", temp_path)
            rows = _parse_vital_import_pdf_payload(raw_text or "")
    except OCRDependencyError as exc:
        detail = str(exc)
        logger.warning(
            "[vital-import-preview] ocr dependency error patient_id=%s detail=%s",
            patient_id,
            detail,
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail=detail) from exc
    except HTTPException as exc:
        logger.warning(
            "[vital-import-preview] failed patient_id=%s detail=%s",
            patient_id,
            exc.detail,
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("[vital-import-preview] unexpected error patient_id=%s", patient_id)
        raise

    preview_row = rows[0]
    warning = None
    if len(rows) > 1:
        warning = "Imported file contains multiple vital entries. Prefilled from the first entry."

    logger.warning(
        "[vital-import-preview] success patient_id=%s rows=%s",
        patient_id,
        len(rows),
    )
    response: dict[str, Any] = {
        "status": "success",
        "patient_id": str(patient_uuid),
        "total_vitals": len(rows),
        "prefill": _vital_row_to_prefill(preview_row),
        "message": "Vital-sign import preview generated.",
    }
    if warning:
        response["warning"] = warning
    return response


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
        description="Text export format inside the ZIP archive (json or pdf).",
    ),
    export_language: ExportLanguage = Query(
        default=ExportLanguage.en,
        alias="lang",
        description="Export language for PDF rendering (vi or en).",
    ),
):
    """
    Export full patient record as ZIP archive.

    Archive includes:
    - Lossless JSON text payload for import compatibility
    - Optional PDF text payload when format=pdf
    - Attached medical files in original formats
    - manifest.json for file mapping during import
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    zip_bytes, filename = _build_patient_global_export_archive(
        supabase,
        patient_uuid=patient_uuid,
        export_format=export_format,
        export_language=export_language,
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
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


@router.post("/patients/{patient_id}/import")
async def import_patient_text_data(
    patient_id: str,
    file: UploadFile = File(...),
):
    """
    Import full patient record from exported ZIP archive.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    file_name = file.filename or "import"
    extension = Path(file_name).suffix.lower()
    if extension not in GLOBAL_IMPORT_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported import file type. Allowed: .zip",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Import file is empty")

    import_format = "zip"
    job = _create_patient_import_job(
        patient_id=str(patient_uuid),
        import_format=import_format,
        file_name=file_name,
    )
    asyncio.create_task(
        _run_patient_import_job(
            job_id=job["job_id"],
            patient_uuid=patient_uuid,
            file_name=file_name,
            import_format=import_format,
            content=content,
        )
    )

    return {
        "status": "accepted",
        "job_id": job["job_id"],
        "patient_id": str(patient_uuid),
        "import_format": import_format,
        "progress": 0,
        "stage": "Queued",
        "message": "Patient import started.",
    }


@router.get("/patients/{patient_id}/import/{job_id}")
async def get_patient_import_status(patient_id: str, job_id: str):
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    job = _get_patient_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    if job.get("patient_id") != str(patient_uuid):
        raise HTTPException(status_code=404, detail="Import job not found for patient")

    response: dict[str, Any] = {
        "job_id": job["job_id"],
        "patient_id": job["patient_id"],
        "import_format": job.get("import_format"),
        "status": job.get("status"),
        "stage": job.get("stage"),
        "progress": job.get("progress", 0),
        "ocr_current_page": job.get("ocr_current_page"),
        "ocr_total_pages": job.get("ocr_total_pages"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }
    if job.get("error"):
        response["error"] = job["error"]
    if isinstance(job.get("result"), dict):
        response["result"] = job["result"]
    return response


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
