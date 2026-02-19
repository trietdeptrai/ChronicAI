"""
Upload Router - File upload and document ingestion endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
from uuid import UUID
import base64
import json
import tempfile
import os
import logging
from pathlib import Path
import uuid

from app.config import settings
from app.db.database import get_supabase
from app.models.schemas import RecordType
from app.services.ocr import OCRDependencyError, extract_text
from app.services.llm import analyze_uploaded_record
from app.services.rag import ingest_document, delete_record_embeddings


router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

# Directory for storing chat images temporarily
CHAT_IMAGES_DIR = Path(tempfile.gettempdir()) / "chronic_ai_chat_images"
CHAT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

IMAGING_RECORD_TYPES = {
    "lab",
    "xray",
    "ecg",
    "ct",
    "mri",
}
MAX_ANALYSIS_IMAGE_BYTES = 6 * 1024 * 1024
ALLOWED_RECORD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def _summary_fallback_analysis(analysis: object) -> str:
    """
    Build a non-null text fallback for analysis_result.
    Works with both JSONB and TEXT DB columns.
    """
    if isinstance(analysis, str):
        text = analysis.strip()
        if text:
            return text[:2000]
        return "AI analysis generated."

    if isinstance(analysis, dict):
        summary = str(analysis.get("summary") or "").strip()
        if summary:
            return summary[:2000]

        findings = analysis.get("key_findings")
        if isinstance(findings, list) and findings:
            first = str(findings[0]).strip()
            if first:
                return first[:2000]

        compact = json.dumps(analysis, ensure_ascii=False)
        if compact:
            return compact[:2000]

    return "AI analysis generated."


def _analysis_summary_text(analysis: object) -> str:
    """
    Extract a compact summary text from analysis payload.
    """
    if isinstance(analysis, str):
        return analysis.strip()
    if isinstance(analysis, dict):
        summary = str(analysis.get("summary") or "").strip()
        if summary:
            return summary
        findings = analysis.get("key_findings")
        if isinstance(findings, list) and findings:
            return "; ".join(str(item).strip() for item in findings if str(item).strip())
    return ""


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _analysis_with_doctor_comment(
    analysis: object,
    doctor_comment: Optional[str]
) -> object:
    """
    Store doctor comment inside analysis payload when DB has no doctor_comment column.
    """
    comment = _normalize_optional_text(doctor_comment)
    if isinstance(analysis, dict):
        payload = dict(analysis)
        if comment:
            payload["doctor_comment"] = comment
        else:
            payload.pop("doctor_comment", None)
        return payload

    if comment:
        summary = analysis.strip() if isinstance(analysis, str) else ""
        payload = {
            "status": "completed",
            "doctor_comment": comment,
        }
        if summary:
            payload["summary"] = summary
        return payload

    return analysis


def _extract_doctor_comment_from_record(record: dict) -> Optional[str]:
    """
    Read doctor comment from dedicated column if available, else analysis metadata.
    """
    comment = _normalize_optional_text(record.get("doctor_comment"))
    analysis = record.get("analysis_result")

    if not comment and isinstance(analysis, dict):
        comment = _normalize_optional_text(analysis.get("doctor_comment"))

    if isinstance(analysis, dict) and "doctor_comment" in analysis:
        cleaned = dict(analysis)
        cleaned.pop("doctor_comment", None)
        record["analysis_result"] = cleaned

    return comment


def _insert_medical_record_with_fallback(
    supabase: object,
    record_data: dict,
    doctor_comment: Optional[str],
    log_prefix: str
) -> tuple[object, object, Optional[str], Optional[str], bool]:
    """
    Insert medical record with compatibility fallbacks:
    1) structured analysis + doctor_comment column
    2) structured analysis + doctor_comment inside analysis JSON
    3) summary-only analysis text
    """
    insert_warning = None
    used_analysis_metadata_comment = False
    stored_analysis = record_data.get("analysis_result")
    stored_comment = _normalize_optional_text(doctor_comment)

    attempt_payload = dict(record_data)
    attempt_payload["doctor_comment"] = stored_comment

    try:
        result = supabase.table("medical_records").insert(attempt_payload).execute()
    except Exception:
        logger.exception("%s insert with doctor_comment column failed", log_prefix)
        result = None

    if result and result.data:
        return result, stored_analysis, stored_comment, insert_warning, used_analysis_metadata_comment

    payload_no_column = dict(record_data)
    payload_no_column["analysis_result"] = _analysis_with_doctor_comment(
        payload_no_column.get("analysis_result"),
        stored_comment
    )
    used_analysis_metadata_comment = bool(stored_comment)
    stored_analysis = payload_no_column.get("analysis_result")

    try:
        result = supabase.table("medical_records").insert(payload_no_column).execute()
    except Exception:
        logger.exception("%s insert without doctor_comment column failed", log_prefix)
        result = None

    if result and result.data:
        if used_analysis_metadata_comment:
            insert_warning = "Stored doctor comment inside analysis payload due DB schema compatibility."
        return result, stored_analysis, stored_comment, insert_warning, used_analysis_metadata_comment

    if payload_no_column.get("analysis_result") is not None:
        fallback_payload = dict(payload_no_column)
        fallback_payload["analysis_result"] = _summary_fallback_analysis(
            payload_no_column["analysis_result"]
        )
        if stored_comment:
            fallback_payload["analysis_result"] = (
                f"{fallback_payload['analysis_result']}\n\nDoctor comment: {stored_comment}"
            )
        stored_analysis = fallback_payload["analysis_result"]

        try:
            result = supabase.table("medical_records").insert(fallback_payload).execute()
        except Exception:
            logger.exception("%s insert with summary-only analysis failed", log_prefix)
            result = None

        if result and result.data:
            if used_analysis_metadata_comment:
                insert_warning = "Stored AI analysis/comment as summary text due DB schema compatibility."
            else:
                insert_warning = "Stored AI analysis as summary text due DB schema/encoding compatibility."
            return result, stored_analysis, stored_comment, insert_warning, used_analysis_metadata_comment

    return None, stored_analysis, stored_comment, insert_warning, used_analysis_metadata_comment


def _validate_record_type(value: str) -> None:
    valid_types = {record_type.value for record_type in RecordType}
    if value not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(sorted(valid_types))}"
        )


def _fetch_record_for_update(
    supabase: object,
    record_id: UUID,
    patient_id: UUID
) -> Optional[dict]:
    try:
        result = supabase.table("medical_records").select(
            "id, patient_id, record_type, title, content_text, image_path, analysis_result, doctor_comment"
        ).eq("id", str(record_id)).eq("patient_id", str(patient_id)).maybe_single().execute()
        data = result.data if result else None
        if isinstance(data, dict):
            return data
    except Exception:
        logger.exception("[record-update] select with doctor_comment column failed")

    try:
        result = supabase.table("medical_records").select(
            "id, patient_id, record_type, title, content_text, image_path, analysis_result"
        ).eq("id", str(record_id)).eq("patient_id", str(patient_id)).maybe_single().execute()
        data = result.data if result else None
        if isinstance(data, dict):
            data["doctor_comment"] = None
            return data
    except Exception:
        logger.exception("[record-update] fallback select failed")
    return None


def _update_record_with_comment_fallback(
    supabase: object,
    record_id: UUID,
    patient_id: UUID,
    update_payload: dict,
    effective_comment: Optional[str],
    existing_analysis: object,
    log_prefix: str
) -> tuple[object, Optional[str], bool]:
    """
    Update record with compatibility fallback if doctor_comment column does not exist.
    """
    normalized_comment = _normalize_optional_text(effective_comment)
    used_analysis_metadata_comment = False
    warning = None

    payload_with_comment = dict(update_payload)
    payload_with_comment["doctor_comment"] = normalized_comment

    try:
        result = supabase.table("medical_records").update(payload_with_comment).eq(
            "id", str(record_id)
        ).eq(
            "patient_id", str(patient_id)
        ).execute()
    except Exception:
        logger.exception("%s update with doctor_comment column failed", log_prefix)
        result = None

    if result and result.data:
        return result, warning, used_analysis_metadata_comment

    payload_no_column = dict(update_payload)
    payload_no_column["analysis_result"] = _analysis_with_doctor_comment(
        payload_no_column.get("analysis_result", existing_analysis),
        normalized_comment
    )
    used_analysis_metadata_comment = True

    try:
        result = supabase.table("medical_records").update(payload_no_column).eq(
            "id", str(record_id)
        ).eq(
            "patient_id", str(patient_id)
        ).execute()
    except Exception:
        logger.exception("%s update without doctor_comment column failed", log_prefix)
        result = None

    if result and result.data and normalized_comment is not None:
        warning = "Stored doctor comment inside analysis payload due DB schema compatibility."

    return result, warning, used_analysis_metadata_comment


def _remove_storage_path(
    supabase: object,
    storage_path: Optional[str],
    log_prefix: str
) -> None:
    if not storage_path:
        return
    try:
        supabase.storage.from_(settings.patient_photo_bucket).remove([storage_path])
    except Exception:
        logger.exception("%s failed to remove storage object path=%s", log_prefix, storage_path)


@router.post("/chat-image")
async def upload_chat_image(
    file: UploadFile = File(...)
):
    """
    Upload an image temporarily for use in chat.
    
    The image will be saved and the file path returned for use
    with the /chat/stream or /chat/doctor/stream endpoints.
    
    Args:
        file: Image file (PNG, JPG, JPEG, etc.)
    
    Returns:
        JSON with the file path to use in chat requests
    """
    # Validate file type
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Generate unique filename
    import uuid
    unique_name = f"{uuid.uuid4()}{file_ext}"
    file_path = CHAT_IMAGES_DIR / unique_name
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "file_path": str(file_path),
            "message": "Image uploaded successfully for chat use"
        }
    )


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    record_type: str = Form(...),
    title: Optional[str] = Form(None),
    doctor_comment: Optional[str] = Form(None)
):
    """
    Upload a medical document (PDF or image).
    
    Process:
    1. Save file temporarily
    2. PDF: OCR extract text
       Image: direct LLM image analysis (OCR optional via config)
    3. Create medical record in database
    4. Generate embeddings and store for RAG
    
    Args:
        file: PDF or image file
        patient_id: Patient UUID
        record_type: Type of document (prescription, lab, xray, ecg, ct, mri, notes, referral)
        title: Optional document title
    """
    # Validate file type
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in ALLOWED_RECORD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_RECORD_EXTENSIONS))}"
        )
    
    _validate_record_type(record_type)
    
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(
        suffix=file_ext,
        delete=False
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        is_pdf = file_ext == ".pdf"
        extracted_text = ""
        if is_pdf or settings.image_upload_run_ocr:
            extracted_text = await extract_text(tmp_path)
        else:
            logger.info("[upload-document] skipping OCR for image upload (image_upload_run_ocr=false)")

        image_base64 = None
        if not is_pdf and len(content) <= MAX_ANALYSIS_IMAGE_BYTES:
            image_base64 = base64.b64encode(content).decode("utf-8")
        analysis_result = await analyze_uploaded_record(
            record_type=record_type,
            title=title or file.filename,
            extracted_text=extracted_text,
            image_base64=image_base64
        )
        if isinstance(analysis_result, dict):
            logger.info(
                "[upload-document] analysis status=%s request_id=%s has_summary=%s",
                analysis_result.get("status"),
                analysis_result.get("request_id"),
                bool(analysis_result.get("summary")),
            )
            if analysis_result.get("status") == "error":
                logger.error(
                    "[upload-document] analysis error request_id=%s limitations=%s",
                    analysis_result.get("request_id"),
                    analysis_result.get("limitations"),
                )
        analysis_summary = _analysis_summary_text(analysis_result)
        content_for_record = extracted_text or analysis_summary or "AI analysis generated for this record."
        
        supabase = get_supabase()
        
        # Upload files (PDFs and images) to Supabase Storage for record viewing
        image_path = None
        bucket = settings.patient_photo_bucket
        unique_name = f"{uuid.uuid4()}{file_ext}"
        storage_path = f"records/{patient_uuid}/{unique_name}"
        content_type = file.content_type or ("application/pdf" if file_ext == ".pdf" else "application/octet-stream")
        
        try:
            upload_result = supabase.storage.from_(bucket).upload(
                storage_path,
                content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )
        
        if isinstance(upload_result, dict) and upload_result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {upload_result['error']}"
            )
        
        image_path = storage_path
        
        # Create medical record entry
        normalized_comment = _normalize_optional_text(doctor_comment)

        record_data = {
            "patient_id": str(patient_uuid),
            "record_type": record_type,
            "title": title or file.filename,
            "content_text": content_for_record,
            "image_path": image_path,
            "analysis_result": analysis_result
        }

        # Ensure analysis payload is JSON-serializable; fallback to null if not.
        try:
            json.dumps(record_data["analysis_result"])
        except Exception:
            record_data["analysis_result"] = None

        (
            result,
            stored_analysis,
            stored_comment,
            insert_warning,
            _,
        ) = _insert_medical_record_with_fallback(
            supabase=supabase,
            record_data=record_data,
            doctor_comment=normalized_comment,
            log_prefix="[upload-document]",
        )
        
        if not result or not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create medical record"
            )
        
        record_id = result.data[0]["id"]
        
        # Ingest into RAG system
        num_chunks = await ingest_document(
            text=content_for_record,
            record_id=UUID(record_id)
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "record_id": record_id,
                "patient_id": patient_id,
                "extracted_text_preview": extracted_text[:500] if extracted_text else "",
                "ai_analysis": stored_analysis,
                "doctor_comment": stored_comment,
                "warning": insert_warning,
                "chunks_created": num_chunks,
                "message": f"Document processed successfully. Created {num_chunks} embeddings."
            }
        )
        
    except OCRDependencyError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/patient-photo")
async def upload_patient_photo(
    patient_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a patient profile photo and update the patient record.
    
    Process:
    1. Validate patient UUID and image type
    2. Upload image to Supabase Storage
    3. Update patients.profile_photo_url
    """
    # Validate file type
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    supabase = get_supabase()
    
    # Ensure patient exists
    patient = supabase.table("patients").select("id").eq(
        "id", str(patient_uuid)
    ).single().execute()
    
    if not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Upload to Supabase Storage
    bucket = settings.patient_photo_bucket
    unique_name = f"{uuid.uuid4()}{file_ext}"
    storage_path = f"patients/{patient_uuid}/{unique_name}"
    
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    
    try:
        upload_result = supabase.storage.from_(bucket).upload(
            storage_path,
            content,
            file_options={
                "content-type": content_type,
                "upsert": "true"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}"
        )
    
    if isinstance(upload_result, dict) and upload_result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {upload_result['error']}"
        )
    
    update_result = supabase.table("patients").update({
        "profile_photo_url": storage_path
    }).eq("id", str(patient_uuid)).execute()
    
    if not update_result.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to update patient profile photo"
        )

    signed = supabase.storage.from_(bucket).create_signed_url(
        storage_path,
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
    
    if not signed_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate signed URL for uploaded image"
        )
    
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "patient_id": patient_id,
            "profile_photo_url": signed_url,
            "message": "Patient photo uploaded successfully"
        }
    )


@router.post("/patient-record-image")
async def upload_patient_record_image(
    patient_id: str = Form(...),
    record_type: str = Form(...),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    doctor_comment: Optional[str] = Form(None)
):
    """
    Upload a patient test-result image (e.g., lab, X-ray, ECG, CT, MRI)
    and create a medical record entry.
    
    Process:
    1. Validate patient UUID and record type
    2. Save image temporarily
    3. LLM analyzes image directly (OCR optional via config)
    4. Upload image to Supabase Storage
    5. Create medical record entry and ingest into RAG
    """
    allowed_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    if record_type not in IMAGING_RECORD_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(sorted(IMAGING_RECORD_TYPES))}"
        )
    
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    logger.info(
        "[upload-record-image] start patient_id=%s record_type=%s filename=%s",
        patient_id,
        record_type,
        file.filename,
    )

    supabase = get_supabase()
    
    patient = supabase.table("patients").select("id").eq(
        "id", str(patient_uuid)
    ).single().execute()
    
    if not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=file_ext,
            delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        logger.info("[upload-record-image] file-buffered size_bytes=%s tmp=%s", len(content), tmp_path)

        extracted_text = ""
        if settings.image_upload_run_ocr:
            try:
                extracted_text = await extract_text(tmp_path)
            except OCRDependencyError as exc:
                raise HTTPException(
                    status_code=503,
                    detail=str(exc),
                ) from exc
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("[upload-record-image] OCR failed")
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR failed: {str(exc)}"
                ) from exc
            logger.info("[upload-record-image] OCR done text_len=%s", len(extracted_text or ""))
        else:
            logger.info("[upload-record-image] OCR disabled for image upload (image_upload_run_ocr=false)")
        image_base64 = None
        if len(content) <= MAX_ANALYSIS_IMAGE_BYTES:
            image_base64 = base64.b64encode(content).decode("utf-8")
        try:
            analysis_result = await analyze_uploaded_record(
                record_type=record_type,
                title=title or file.filename,
                extracted_text=extracted_text,
                image_base64=image_base64
            )
        except Exception as exc:
            logger.exception("[upload-record-image] analysis call crashed")
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis failed: {str(exc)}"
            ) from exc
        logger.info(
            "[upload-record-image] analysis status=%s request_id=%s has_summary=%s",
            (analysis_result or {}).get("status") if isinstance(analysis_result, dict) else "unknown",
            (analysis_result or {}).get("request_id") if isinstance(analysis_result, dict) else None,
            bool((analysis_result or {}).get("summary")) if isinstance(analysis_result, dict) else bool(analysis_result),
        )
        if isinstance(analysis_result, dict) and analysis_result.get("status") == "error":
            logger.error(
                "[upload-record-image] analysis error request_id=%s limitations=%s",
                analysis_result.get("request_id"),
                analysis_result.get("limitations"),
            )
        analysis_summary = _analysis_summary_text(analysis_result)
        content_for_record = extracted_text or analysis_summary or "AI analysis generated for this record."
        
        bucket = settings.patient_photo_bucket
        unique_name = f"{uuid.uuid4()}{file_ext}"
        storage_path = f"records/{patient_uuid}/{unique_name}"
        content_type = file.content_type or "application/octet-stream"
        
        try:
            upload_result = supabase.storage.from_(bucket).upload(
                storage_path,
                content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {str(e)}"
            )
        logger.info("[upload-record-image] storage upload ok path=%s", storage_path)
        
        if isinstance(upload_result, dict) and upload_result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {upload_result['error']}"
            )
        
        normalized_comment = _normalize_optional_text(doctor_comment)

        record_data = {
            "patient_id": str(patient_uuid),
            "record_type": record_type,
            "title": title or file.filename,
            "content_text": content_for_record,
            "image_path": storage_path,
            "analysis_result": analysis_result
        }

        # Ensure analysis payload is JSON-serializable; fallback to null if not.
        try:
            json.dumps(record_data["analysis_result"])
        except Exception:
            record_data["analysis_result"] = None

        (
            result,
            stored_analysis,
            stored_comment,
            insert_warning,
            _,
        ) = _insert_medical_record_with_fallback(
            supabase=supabase,
            record_data=record_data,
            doctor_comment=normalized_comment,
            log_prefix="[upload-record-image]",
        )
        logger.info("[upload-record-image] db insert ok=%s warning=%s", bool(result and result.data), bool(insert_warning))
        
        if not result or not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create medical record"
            )
        
        record_id = result.data[0]["id"]
        
        try:
            num_chunks = await ingest_document(
                text=content_for_record,
                record_id=UUID(record_id)
            )
        except Exception as exc:
            logger.exception("[upload-record-image] embedding ingestion failed record_id=%s", record_id)
            raise HTTPException(
                status_code=500,
                detail=f"Embedding ingestion failed: {str(exc)}"
            ) from exc
        logger.info("[upload-record-image] ingest done chunks=%s", num_chunks)
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "record_id": record_id,
                "patient_id": patient_id,
                "extracted_text_preview": extracted_text[:500] if extracted_text else "",
                "ai_analysis": stored_analysis,
                "doctor_comment": stored_comment,
                "warning": insert_warning,
                "chunks_created": num_chunks,
                "message": "Record image uploaded successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[upload-record-image] unexpected failure")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process record image: {str(e)}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/text")
async def upload_text(
    patient_id: str = Form(...),
    record_type: str = Form(...),
    content: str = Form(...),
    title: Optional[str] = Form(None),
    doctor_comment: Optional[str] = Form(None)
):
    """
    Upload text content directly (e.g., typed notes).
    
    Args:
        patient_id: Patient UUID
        record_type: Type of record
        content: Text content
        title: Optional title
    """
    _validate_record_type(record_type)
    
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    supabase = get_supabase()
    
    normalized_comment = _normalize_optional_text(doctor_comment)

    # Create medical record
    record_data = {
        "patient_id": str(patient_uuid),
        "record_type": record_type,
        "title": title or "Text Note",
        "content_text": content,
        "image_path": None,
        "analysis_result": None
    }

    (
        result,
        _stored_analysis,
        stored_comment,
        insert_warning,
        _,
    ) = _insert_medical_record_with_fallback(
        supabase=supabase,
        record_data=record_data,
        doctor_comment=normalized_comment,
        log_prefix="[upload-text]",
    )
    
    if not result or not result.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to create medical record"
        )
    
    record_id = result.data[0]["id"]
    
    # Ingest into RAG
    num_chunks = await ingest_document(
        text=content,
        record_id=UUID(record_id)
    )
    
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "record_id": record_id,
            "patient_id": patient_id,
            "doctor_comment": stored_comment,
            "warning": insert_warning,
            "chunks_created": num_chunks,
            "message": "Text record created successfully"
        }
    )


@router.put("/patient-record/{record_id}")
async def update_patient_record(
    record_id: str,
    patient_id: str = Form(...),
    doctor_comment: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    record_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Update a medical record.

    Supported operations:
    - Update doctor comment only.
    - Re-upload file and rerun AI analysis.
    - Optionally update title/record_type together.
    """
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record_id format")

    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    existing = _fetch_record_for_update(supabase, record_uuid, patient_uuid)
    if not existing:
        raise HTTPException(status_code=404, detail="Medical record not found")

    existing_comment = _extract_doctor_comment_from_record(existing)
    comment_was_provided = doctor_comment is not None
    effective_comment = (
        _normalize_optional_text(doctor_comment)
        if comment_was_provided
        else existing_comment
    )

    provided_title = title is not None
    normalized_title = _normalize_optional_text(title)
    effective_title = normalized_title if provided_title else existing.get("title")

    provided_record_type = record_type is not None
    effective_record_type = record_type or existing.get("record_type")
    if effective_record_type:
        _validate_record_type(effective_record_type)

    if not file and not comment_was_provided and not provided_title and not provided_record_type:
        raise HTTPException(
            status_code=400,
            detail="No changes requested. Provide doctor_comment, title, record_type, or file."
        )

    update_payload: dict = {}
    old_storage_path = existing.get("image_path")
    new_storage_path: Optional[str] = None
    tmp_path: Optional[str] = None
    num_chunks: Optional[int] = None
    stored_analysis: object = existing.get("analysis_result")
    warning: Optional[str] = None

    if provided_title:
        update_payload["title"] = effective_title
    if provided_record_type and effective_record_type:
        update_payload["record_type"] = effective_record_type

    try:
        if file:
            file_ext = Path(file.filename).suffix.lower() if file.filename else ""
            if file_ext not in ALLOWED_RECORD_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_RECORD_EXTENSIONS))}"
                )

            if not effective_record_type:
                raise HTTPException(status_code=400, detail="record_type is required")

            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            is_pdf = file_ext == ".pdf"
            extracted_text = ""
            if is_pdf or settings.image_upload_run_ocr:
                extracted_text = await extract_text(tmp_path)
            else:
                logger.info("[record-update] OCR disabled for image upload (image_upload_run_ocr=false)")

            image_base64 = None
            if not is_pdf and len(content) <= MAX_ANALYSIS_IMAGE_BYTES:
                image_base64 = base64.b64encode(content).decode("utf-8")

            try:
                analysis_result = await analyze_uploaded_record(
                    record_type=effective_record_type,
                    title=effective_title or file.filename or existing.get("title"),
                    extracted_text=extracted_text,
                    image_base64=image_base64,
                )
            except Exception as exc:
                logger.exception("[record-update] AI analysis failed record_id=%s", record_id)
                raise HTTPException(
                    status_code=500,
                    detail="AI analysis failed while updating this record."
                ) from exc

            stored_analysis = analysis_result
            content_for_record = (
                extracted_text
                or _analysis_summary_text(analysis_result)
                or "AI analysis generated for this record."
            )
            effective_title = effective_title or file.filename or existing.get("title") or "Medical record"

            unique_name = f"{uuid.uuid4()}{file_ext}"
            new_storage_path = f"records/{patient_uuid}/{unique_name}"
            content_type = file.content_type or ("application/pdf" if is_pdf else "application/octet-stream")

            upload_result = supabase.storage.from_(settings.patient_photo_bucket).upload(
                new_storage_path,
                content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true",
                }
            )
            if isinstance(upload_result, dict) and upload_result.get("error"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload replacement file: {upload_result['error']}"
                )

            update_payload["record_type"] = effective_record_type
            update_payload["title"] = effective_title
            update_payload["content_text"] = content_for_record
            update_payload["image_path"] = new_storage_path
            update_payload["analysis_result"] = analysis_result

            # Ensure analysis payload is JSON-serializable.
            try:
                json.dumps(update_payload["analysis_result"])
            except Exception:
                update_payload["analysis_result"] = None
                stored_analysis = None

        result, update_warning, _used_metadata_comment = _update_record_with_comment_fallback(
            supabase=supabase,
            record_id=record_uuid,
            patient_id=patient_uuid,
            update_payload=update_payload,
            effective_comment=effective_comment,
            existing_analysis=existing.get("analysis_result"),
            log_prefix="[record-update]",
        )
        warning = update_warning

        if not result or not result.data:
            raise HTTPException(status_code=500, detail="Failed to update medical record")

        updated_record = result.data[0]

        if file:
            try:
                await delete_record_embeddings(record_uuid)
                num_chunks = await ingest_document(
                    text=update_payload["content_text"],
                    record_id=record_uuid,
                )
            except Exception:
                logger.exception("[record-update] embedding refresh failed record_id=%s", record_id)
                if warning:
                    warning = f"{warning} Embedding refresh failed."
                else:
                    warning = "Embedding refresh failed."

            if old_storage_path and old_storage_path != new_storage_path:
                _remove_storage_path(supabase, old_storage_path, "[record-update]")

        merged_record = dict(updated_record)
        merged_record["analysis_result"] = update_payload.get("analysis_result", stored_analysis)
        merged_record["doctor_comment"] = effective_comment
        if warning:
            merged_record["warning"] = warning

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "record_id": record_id,
                "patient_id": patient_id,
                "doctor_comment": effective_comment,
                "ai_analysis": merged_record.get("analysis_result"),
                "chunks_created": num_chunks,
                "warning": warning,
                "message": "Medical record updated successfully",
            }
        )
    except OCRDependencyError as exc:
        if new_storage_path:
            _remove_storage_path(supabase, new_storage_path, "[record-update]")
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except HTTPException:
        # Roll back newly uploaded file on failure before DB save.
        if new_storage_path:
            _remove_storage_path(supabase, new_storage_path, "[record-update]")
        raise
    except Exception as exc:
        if new_storage_path:
            _remove_storage_path(supabase, new_storage_path, "[record-update]")
        logger.exception("[record-update] unexpected failure record_id=%s", record_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update medical record: {str(exc)}"
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.delete("/patient-record/{record_id}")
async def delete_patient_record(
    record_id: str,
    patient_id: str
):
    """
    Delete a medical record, associated file, and embeddings.
    """
    try:
        record_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record_id format")

    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    supabase = get_supabase()
    existing = _fetch_record_for_update(supabase, record_uuid, patient_uuid)
    if not existing:
        raise HTTPException(status_code=404, detail="Medical record not found")

    delete_result = supabase.table("medical_records").delete().eq(
        "id", str(record_uuid)
    ).eq(
        "patient_id", str(patient_uuid)
    ).execute()

    if not delete_result or not delete_result.data:
        raise HTTPException(status_code=500, detail="Failed to delete medical record")

    try:
        await delete_record_embeddings(record_uuid)
    except Exception:
        logger.exception("[record-delete] failed to delete embeddings record_id=%s", record_id)

    _remove_storage_path(supabase, existing.get("image_path"), "[record-delete]")

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "record_id": record_id,
            "patient_id": patient_id,
            "message": "Medical record deleted successfully",
        }
    )
