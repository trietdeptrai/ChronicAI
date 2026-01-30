"""
Chat Router - AI-powered medical chat endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import json

from app.services.llm import process_medical_query


router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """Chat request model."""
    patient_id: str
    message: str
    image_path: Optional[str] = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    response: str
    response_en: Optional[str] = None
    patient_id: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the medical AI assistant.
    
    Uses the Translation Sandwich pipeline:
    1. Vietnamese → English translation
    2. MedGemma medical reasoning with RAG context
    3. English → Vietnamese translation
    
    Returns full response (non-streaming).
    """
    try:
        patient_uuid = UUID(request.patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    final_response = None
    response_en = None
    
    # Process through pipeline and get final result
    async for update in process_medical_query(
        user_input_vi=request.message,
        patient_id=patient_uuid,
        image_path=request.image_path
    ):
        if update.get("stage") == "complete":
            final_response = update.get("response", "")
            response_en = update.get("response_en")
    
    if not final_response:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate response"
        )
    
    return ChatResponse(
        response=final_response,
        response_en=response_en,
        patient_id=request.patient_id
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message with streaming response.
    
    Returns Server-Sent Events (SSE) with progress updates:
    - translating_input: Translating Vietnamese to English
    - retrieving_context: Searching medical records
    - medical_reasoning: MedGemma processing
    - translating_output: Translating response to Vietnamese
    - complete: Final response ready
    
    Each event contains:
    - stage: Current processing stage
    - message: Vietnamese status message
    - progress: 0.0 to 1.0
    - Additional data depending on stage
    """
    try:
        patient_uuid = UUID(request.patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    async def event_generator():
        """Generate SSE events."""
        try:
            async for update in process_medical_query(
                user_input_vi=request.message,
                patient_id=patient_uuid,
                image_path=request.image_path
            ):
                # Format as SSE
                data = json.dumps(update, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            error_data = json.dumps({
                "stage": "error",
                "message": f"Lỗi: {str(e)}",
                "error": str(e)
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/history/{patient_id}")
async def get_chat_history(patient_id: str, limit: int = 20):
    """
    Get recent consultation history for a patient.
    
    Args:
        patient_id: Patient UUID
        limit: Maximum number of consultations to return
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    from app.db.database import get_supabase
    
    supabase = get_supabase()
    
    result = supabase.table("consultations").select(
        "id, chief_complaint, status, priority, started_at, ended_at, messages"
    ).eq(
        "patient_id", str(patient_uuid)
    ).order(
        "started_at", desc=True
    ).limit(limit).execute()
    
    return {
        "patient_id": patient_id,
        "consultations": result.data or []
    }
