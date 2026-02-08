"""
Upload Router - File upload and document ingestion endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
from uuid import UUID
import tempfile
import os
from pathlib import Path
import uuid

from app.config import settings
from app.db.database import get_supabase
from app.models.schemas import RecordType
from app.services.ocr import extract_text
from app.services.rag import ingest_document, ingest_image


router = APIRouter(prefix="/upload", tags=["Upload"])

# Directory for storing chat images temporarily
CHAT_IMAGES_DIR = Path(tempfile.gettempdir()) / "chronic_ai_chat_images"
CHAT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

IMAGING_RECORD_TYPES = {
    "xray",
    "ecg",
    "ct",
    "mri",
}


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
    title: Optional[str] = Form(None)
):
    """
    Upload a medical document (PDF or image).
    
    Process:
    1. Save file temporarily
    2. OCR extract text
    3. Create medical record in database
    4. Generate embeddings and store for RAG
    
    Args:
        file: PDF or image file
        patient_id: Patient UUID
        record_type: Type of document (prescription, lab, xray, ecg, ct, mri, notes, referral)
        title: Optional document title
    """
    # Validate file type
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Validate record type
    valid_types = {record_type.value for record_type in RecordType}
    if record_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(sorted(valid_types))}"
        )
    
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
        # Extract text via OCR
        extracted_text = await extract_text(tmp_path)
        
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
        record_data = {
            "patient_id": str(patient_uuid),
            "record_type": record_type,
            "title": title or file.filename,
            "content_text": extracted_text,
            "image_path": image_path,
            "analysis_result": None
        }
        
        result = supabase.table("medical_records").insert(record_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create medical record"
            )
        
        record_id = result.data[0]["id"]
        
        # Ingest into RAG system
        if file_ext == ".pdf":
            num_chunks = await ingest_document(
                text=extracted_text,
                record_id=UUID(record_id)
            )
        else:
            num_chunks = await ingest_image(
                image_text=extracted_text,
                record_id=UUID(record_id)
            )
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "record_id": record_id,
                "patient_id": patient_id,
                "extracted_text_preview": extracted_text[:500] if extracted_text else "",
                "chunks_created": num_chunks,
                "message": f"Document processed successfully. Created {num_chunks} embeddings."
            }
        )
        
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
    title: Optional[str] = Form(None)
):
    """
    Upload a patient imaging study (e.g., X-ray, ECG, CT, MRI) and create a medical record entry.
    
    Process:
    1. Validate patient UUID and record type
    2. Save image temporarily for OCR
    3. Upload image to Supabase Storage
    4. Create medical record entry and ingest into RAG
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
        
        extracted_text = await extract_text(tmp_path)
        
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
        
        if isinstance(upload_result, dict) and upload_result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {upload_result['error']}"
            )
        
        record_data = {
            "patient_id": str(patient_uuid),
            "record_type": record_type,
            "title": title or file.filename,
            "content_text": extracted_text,
            "image_path": storage_path,
            "analysis_result": None
        }
        
        result = supabase.table("medical_records").insert(record_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create medical record"
            )
        
        record_id = result.data[0]["id"]
        
        num_chunks = await ingest_image(
            image_text=extracted_text,
            record_id=UUID(record_id)
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "record_id": record_id,
                "patient_id": patient_id,
                "extracted_text_preview": extracted_text[:500] if extracted_text else "",
                "chunks_created": num_chunks,
                "message": "Record image uploaded successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
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
    title: Optional[str] = Form(None)
):
    """
    Upload text content directly (e.g., typed notes).
    
    Args:
        patient_id: Patient UUID
        record_type: Type of record
        content: Text content
        title: Optional title
    """
    valid_types = {record_type.value for record_type in RecordType}
    if record_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(sorted(valid_types))}"
        )
    
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    supabase = get_supabase()
    
    # Create medical record
    record_data = {
        "patient_id": str(patient_uuid),
        "record_type": record_type,
        "title": title or "Text Note",
        "content_text": content,
        "image_path": None,
        "analysis_result": None
    }
    
    result = supabase.table("medical_records").insert(record_data).execute()
    
    if not result.data:
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
            "chunks_created": num_chunks,
            "message": "Text record created successfully"
        }
    )
