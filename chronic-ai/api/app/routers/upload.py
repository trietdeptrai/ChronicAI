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

from app.db.database import get_supabase
from app.services.ocr import extract_text
from app.services.rag import ingest_document, ingest_image


router = APIRouter(prefix="/upload", tags=["Upload"])

# Directory for storing chat images temporarily
CHAT_IMAGES_DIR = Path(tempfile.gettempdir()) / "chronic_ai_chat_images"
CHAT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


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
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
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
        record_type: Type of document (prescription, lab, xray, ecg, notes)
        title: Optional document title
    """
    # Validate file type
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate record type
    valid_types = ["prescription", "lab", "xray", "ecg", "notes", "referral"]
    if record_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(valid_types)}"
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
        
        # Create medical record entry
        record_data = {
            "patient_id": str(patient_uuid),
            "record_type": record_type,
            "title": title or file.filename,
            "content_text": extracted_text,
            "image_path": None,  # Could be updated if storing to Supabase Storage
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
    valid_types = ["prescription", "lab", "xray", "ecg", "notes", "referral"]
    if record_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record type. Allowed: {', '.join(valid_types)}"
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
