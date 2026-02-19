"""
Chat Router - AI-powered medical chat endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
import json

from app.services.llm import process_medical_query
from app.services.orchestrator import process_doctor_query
# LangGraph-based orchestration (NEW)
from app.services.doctor_graph import process_doctor_query_graph
from app.services.patient_graph import process_patient_chat_graph
from app.services.output_formatter import format_as_plain_text
from app.services import chat_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


class DoctorChatRequest(BaseModel):
    """Doctor orchestrator chat request - no patient_id required."""
    message: str
    image_path: Optional[str] = None


class DoctorChatRequestV2(BaseModel):
    """
    Enhanced doctor chat request with LangGraph orchestration.
    
    Supports human-in-the-loop (HITL) and formatted output.
    """
    message: str
    image_path: Optional[str] = None
    enable_hitl: bool = Field(
        default=True,
        description="Legacy global HITL toggle (fallback default for feature-specific toggles)"
    )
    enable_llm_hitl: Optional[bool] = Field(
        default=None,
        description="Enable LLM-based HITL (input verification + safety review)"
    )
    enable_patient_confirmation_hitl: Optional[bool] = Field(
        default=None,
        description="Enable non-LLM HITL for ambiguous patient matching confirmation"
    )
    output_format: Literal["plain", "structured", "markdown"] = Field(
        default="structured",
        description="Output format: plain text, structured JSON, or markdown"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for conversation state persistence"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID for chat history persistence"
    )
    doctor_id: Optional[str] = Field(
        default=None,
        description="Doctor UUID for creating new conversations"
    )


class HITLResumeRequest(BaseModel):
    """Request to resume HITL-paused conversation."""
    thread_id: str
    response: dict = Field(
        ...,
        description="Human response to HITL request (e.g., {'action': 'approve'})"
    )


class ChatRequest(BaseModel):
    """Chat request model."""
    patient_id: str
    message: str
    image_path: Optional[str] = None


class ChatRequestV2(BaseModel):
    """
    Enhanced patient chat request with LangGraph.
    """
    patient_id: str
    message: str
    image_path: Optional[str] = None
    output_format: Literal["plain", "structured", "markdown"] = Field(
        default="structured",
        description="Output format: plain text, structured JSON, or markdown"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID for chat history persistence"
    )


class CreateConversationRequest(BaseModel):
    """Request to create a new chat conversation."""
    conversation_type: Literal["doctor", "patient"]
    user_id: str
    title: Optional[str] = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    response: str
    patient_id: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the medical AI assistant.
    
    Uses the medical reasoning pipeline with RAG context.
    
    Returns full response (non-streaming).
    """
    try:
        patient_uuid = UUID(request.patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    final_response = None
    # Process through pipeline and get final result
    async for update in process_medical_query(
        user_input_vi=request.message,
        patient_id=patient_uuid,
        image_path=request.image_path
    ):
        if update.get("stage") == "complete":
            final_response = update.get("response", "")
    
    if not final_response:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate response"
        )
    
    return ChatResponse(
        response=final_response,
        patient_id=request.patient_id
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message with streaming response.
    
    Returns Server-Sent Events (SSE) with progress updates.
    
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


@router.post("/doctor/stream")
async def doctor_chat_stream(request: DoctorChatRequest):
    """
    Doctor orchestrator chat with streaming response.
    
    This endpoint allows doctors to ask about any patient without
    pre-selecting them. The AI will:
    1. Extract patient mentions from the query
    2. Resolve patients from database
    3. Retrieve relevant context
    4. Generate comprehensive response
    
    Returns Server-Sent Events (SSE) with progress updates including:
    - extracting_patients: Identifying mentioned patients
    - resolving_patients: Finding patient records
    - retrieving_context: Gathering medical context
    - medical_reasoning: AI processing
    - complete: Final response ready
    
    Each 'complete' event includes:
    - response: Vietnamese response
    - mentioned_patients: List of identified patients
    """
    async def event_generator():
        """Generate SSE events."""
        try:
            async for update in process_doctor_query(
                query_vi=request.message,
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


# ============================================================================
# NEW: LangGraph-based Orchestration with HITL
# ============================================================================

@router.post("/doctor/v2/stream")
async def doctor_chat_stream_v2(request: DoctorChatRequestV2):
    """
    **NEW** Enhanced doctor orchestrator with LangGraph.
    
    Features:
    - **Human-in-the-Loop (HITL)**: Pauses for human approval on ambiguous 
      queries or high-risk responses
    - **Input Verification**: Uses the configured verification model to validate query clarity
    - **Safety Checks**: Reviews responses for medical safety
    - **Structured Output**: Returns formatted sections (assessment, 
      recommendations, warnings)
    - **Chat History**: Persists messages when conversation_id is provided
    
    When HITL is triggered, the stream will emit:
    ```json
    {
        "stage": "hitl_required",
        "hitl_request": {
            "type": "clarification_needed|approval_required|patient_confirmation",
            "message": "Vietnamese message for UI",
            "details": {...},
            "options": ["option1", "option2"]
        }
    }
    ```
    
    To resume after HITL, use `/chat/doctor/v2/resume`.
    
    Args:
        message: Doctor's query in Vietnamese
        image_path: Optional path to medical image
        enable_hitl: Legacy global HITL fallback (default: true)
        enable_llm_hitl: Enable LLM-based HITL checks
        enable_patient_confirmation_hitl: Enable non-LLM patient confirmation HITL
        output_format: "plain", "structured", or "markdown"
        thread_id: Optional ID for conversation state persistence
        conversation_id: Optional ID for chat history persistence
        doctor_id: Doctor UUID for creating new conversations
    """
    import uuid as uuid_lib
    
    # Generate thread ID if not provided
    thread_id = request.thread_id or str(uuid_lib.uuid4())

    # --- Chat history: resolve or create conversation ---
    conversation_id = request.conversation_id
    if not conversation_id and request.doctor_id:
        try:
            conv = chat_history_service.create_conversation(
                conversation_type="doctor",
                user_id=request.doctor_id,
            )
            conversation_id = conv["id"]
        except Exception as e:
            logger.warning("Failed to create conversation: %s", e)

    # Save user message
    if conversation_id:
        try:
            chat_history_service.save_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={"image_path": request.image_path} if request.image_path else None,
            )
        except Exception as e:
            logger.warning("Failed to save user message: %s", e)
    
    async def event_generator():
        """Generate SSE events from LangGraph."""
        assistant_saved = False
        try:
            async for update in process_doctor_query_graph(
                query_vi=request.message,
                image_path=request.image_path,
                thread_id=thread_id,
                enable_hitl=request.enable_hitl,
                enable_llm_hitl=request.enable_llm_hitl,
                enable_patient_confirmation_hitl=request.enable_patient_confirmation_hitl,
            ):
                # Add thread_id and conversation_id to updates
                update["thread_id"] = thread_id
                if conversation_id:
                    update["conversation_id"] = conversation_id
                
                # Transform output based on requested format
                if update.get("stage") == "complete" and request.output_format == "plain":
                    formatted = update.get("formatted_response")
                    if formatted:
                        update["response_formatted"] = format_as_plain_text(formatted)

                # Save assistant response to history
                if (
                    update.get("stage") == "complete"
                    and conversation_id
                    and not assistant_saved
                ):
                    try:
                        response_text = str(update.get("response", "")).strip()
                        if not response_text:
                            # Some workflows may emit intermediate/empty complete events.
                            # Persist only meaningful final assistant content.
                            continue
                        metadata = {}
                        if update.get("mentioned_patients"):
                            metadata["mentioned_patients"] = update["mentioned_patients"]
                        if update.get("safety_score") is not None:
                            metadata["safety_score"] = update["safety_score"]
                        if update.get("attachments"):
                            metadata["attachments"] = update["attachments"]
                        chat_history_service.save_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=response_text,
                            metadata=metadata or None,
                        )
                        assistant_saved = True
                    except Exception as e:
                        logger.warning("Failed to save assistant message: %s", e)
                
                # Format as SSE
                data = json.dumps(update, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
        except Exception as e:
            error_data = json.dumps({
                "stage": "error",
                "message": f"Lỗi: {str(e)}",
                "error": str(e),
                "thread_id": thread_id
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


@router.post("/doctor/v2/resume")
async def doctor_chat_resume_hitl(request: HITLResumeRequest):
    """
    Resume a HITL-paused conversation.
    
    After receiving a `hitl_required` event, call this endpoint with:
    - thread_id: The thread_id from the HITL event
    - response: Human decision (e.g., `{"action": "approve"}` or 
      `{"query": "clarified query text"}`)
    
    The conversation will resume from where it paused and complete
    processing with the human input.
    """
    from langgraph.types import Command
    from app.services.doctor_graph import get_doctor_graph
    
    graph = get_doctor_graph()
    config = {"configurable": {"thread_id": request.thread_id}}
    
    async def event_generator():
        """Generate SSE events after HITL resume."""
        try:
            # Resume graph with human response
            async for event in graph.astream(
                Command(resume=request.response),
                config=config
            ):
                for node_name, node_output in event.items():
                    if node_name == "__interrupt__":
                        # Another HITL interrupt
                        yield f"data: {json.dumps({'stage': 'hitl_required', 'hitl_request': node_output[0].value, 'thread_id': request.thread_id}, ensure_ascii=False)}\n\n"
                        continue
                    
                    if isinstance(node_output, dict):
                        stage_messages = node_output.get("stage_messages", [])
                        for msg in stage_messages:
                            msg["thread_id"] = request.thread_id
                            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            
            # Get final state
            final_state = graph.get_state(config).values
            
            completion = {
                "stage": "complete",
                "message": "Hoàn thành",
                "progress": 1.0,
                "response": final_state.get("response_vi", ""),
                "formatted_response": final_state.get("formatted_response"),
                "mentioned_patients": [
                    {"id": m["id"], "name": m["name"]}
                    for m in final_state.get("matched_patients", [])
                ],
                "thread_id": request.thread_id
            }
            yield f"data: {json.dumps(completion, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_data = json.dumps({
                "stage": "error",
                "message": f"Lỗi khi tiếp tục: {str(e)}",
                "error": str(e),
                "thread_id": request.thread_id
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


@router.post("/patient/v2/stream")
async def patient_chat_stream_v2(request: ChatRequestV2):
    """
    **NEW** Enhanced patient chat with LangGraph.
    
    Features:
    - **Symptom Triage**: Auto-detects emergency/urgent cases
    - **Safety Escalation**: Redirects high-risk cases to hospital
    - **Context Awareness**: Retains patient history
    - **Structured Output**: Clear formatting
    - **Chat History**: Persists messages when conversation_id is provided
    
    Args:
        patient_id: Patient UUID
        message: Patient's query in Vietnamese
        image_path: Optional path to medical image
        output_format: "plain", "structured", or "markdown"
        conversation_id: Optional ID for chat history persistence
    """
    try:
        patient_uuid = UUID(request.patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient_id format")

    # --- Chat history: resolve or create conversation ---
    conversation_id = request.conversation_id
    if not conversation_id:
        try:
            conv = chat_history_service.create_conversation(
                conversation_type="patient",
                user_id=request.patient_id,
            )
            conversation_id = conv["id"]
        except Exception as e:
            logger.warning("Failed to create conversation: %s", e)

    # Save user message
    if conversation_id:
        try:
            chat_history_service.save_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={"image_path": request.image_path} if request.image_path else None,
            )
        except Exception as e:
            logger.warning("Failed to save user message: %s", e)

    async def event_generator():
        """Generate SSE events from LangGraph."""
        assistant_saved = False
        try:
            async for update in process_patient_chat_graph(
                patient_id=request.patient_id,
                query_vi=request.message,
                image_path=request.image_path
            ):
                # Add conversation_id to updates
                if conversation_id:
                    update["conversation_id"] = conversation_id

                # Transform output based on requested format
                if update.get("stage") == "complete" and request.output_format == "plain":
                    formatted = update.get("formatted_response")
                    if formatted:
                        update["response_formatted"] = format_as_plain_text(formatted)

                # Save assistant response to history
                if (
                    update.get("stage") == "complete"
                    and conversation_id
                    and not assistant_saved
                ):
                    try:
                        response_text = str(update.get("response", "")).strip()
                        if not response_text:
                            # Some workflows may emit intermediate/empty complete events.
                            # Persist only meaningful final assistant content.
                            continue
                        metadata = {}
                        if update.get("attachments"):
                            metadata["attachments"] = update["attachments"]
                        chat_history_service.save_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=response_text,
                            metadata=metadata or None,
                        )
                        assistant_saved = True
                    except Exception as e:
                        logger.warning("Failed to save assistant message: %s", e)
                
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


# ============================================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================================


@router.get("/conversations/{conversation_type}")
async def list_conversations(
    conversation_type: str,
    user_id: str = Query(..., description="Doctor or patient UUID"),
    limit: int = Query(default=50, le=100),
):
    """
    List chat conversations for a user.
    
    Args:
        conversation_type: 'doctor' or 'patient'
        user_id: The doctor or patient UUID
        limit: Max conversations to return
    """
    if conversation_type not in ("doctor", "patient"):
        raise HTTPException(status_code=400, detail="conversation_type must be 'doctor' or 'patient'")

    try:
        UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    conversations = chat_history_service.get_conversations(
        conversation_type=conversation_type,
        user_id=user_id,
        limit=limit,
    )
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=100, le=500),
):
    """
    Get messages for a specific conversation.
    """
    try:
        UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    messages = chat_history_service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
    )
    return {"conversation_id": conversation_id, "messages": messages}


@router.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new chat conversation.
    """
    try:
        UUID(request.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    conversation = chat_history_service.create_conversation(
        conversation_type=request.conversation_type,
        user_id=request.user_id,
        title=request.title,
    )
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.
    """
    try:
        UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    deleted = chat_history_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "conversation_id": conversation_id}
