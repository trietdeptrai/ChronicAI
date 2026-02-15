"""
LLM Service.
"""
from typing import Any, AsyncGenerator, Optional
from uuid import UUID
import base64
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import uuid

from app.services.llm_client import llm_client
from app.services.rag import get_patient_context
from app.config import settings

logger = logging.getLogger(__name__)

# System prompt for MedGemma medical reasoning
MEDICAL_REASONING_SYSTEM = """You are a helpful medical AI assistant for Vietnamese healthcare.
You assist doctors and patients with chronic disease management.
Use the provided patient context to give accurate, personalized responses.

IMPORTANT GUIDELINES:
- Be thorough but concise in your explanations
- Always consider the patient's medical history and current medications
- Flag any potential drug interactions or contraindications
- For serious symptoms, recommend seeking immediate medical attention
- Explain medical concepts in simple terms when addressing patients
- Include relevant warnings about symptoms that require urgent care

CRITICAL - HANDLING MISSING DATA:
- NEVER output placeholder text like [Insert...], [TODO], [N/A], [Date unknown], etc.
- NEVER use bracket notation to indicate missing information
- If specific data is not available in the provided context, state it naturally
- Example: Instead of "[Insert Last Checkup Date]", say "This information is not available in your records"
- Only answer based on information actually present in the patient context
- If important data is missing, suggest checking with the healthcare provider

Remember: You are a support tool, not a replacement for professional medical advice."""

UPLOAD_ANALYSIS_SYSTEM = """You are a clinical decision-support assistant for doctors.
Analyze uploaded medical records and produce concise, practical insights.
You must return valid JSON only (no markdown or extra commentary)."""


def _extract_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    """Extract first JSON object from a model response."""
    if not raw_text:
        return None

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", raw_text)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    except Exception:
        return None

    return None


def _to_string_list(value: Any, max_items: int = 5) -> list[str]:
    """Normalize a model field into a list of non-empty strings."""
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [value]
    else:
        return []

    cleaned: list[str] = []
    for item in items:
        item_str = str(item).strip()
        if item_str:
            cleaned.append(item_str)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _sanitize_text(value: Any, max_len: int = 1200) -> str:
    """
    Normalize text for safe DB JSON storage.

    Removes null/control chars that commonly break JSONB insertion.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    # Remove null bytes first.
    text = text.replace("\x00", " ")
    # Keep printable chars and common whitespace.
    text = "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ord(ch) >= 32)
    # Drop invalid unicode code points for storage safety.
    text = text.encode("utf-8", "ignore").decode("utf-8")
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def _sanitize_list(values: list[str], max_items: int = 5, max_item_len: int = 400) -> list[str]:
    """Sanitize a list of strings for storage safety."""
    out: list[str] = []
    for value in values[:max_items]:
        cleaned = _sanitize_text(value, max_len=max_item_len)
        if cleaned:
            out.append(cleaned)
    return out


def _classify_llm_error(message: str) -> str:
    """Convert low-level LLM errors into backend diagnostic reason text."""
    msg = (message or "").lower()
    if "notimplementederror" in msg:
        return "Server runtime does not support async subprocess execution for token retrieval."
    if "not found" in msg and "model" in msg:
        return "Configured model is unavailable. Please verify MEDICAL_MODEL in backend configuration."
    if "gcloud" in msg or "access token" in msg or "auth" in msg:
        return "Google Cloud authentication is unavailable for this server session."
    if "vertex ai error (401)" in msg or "vertex ai error (403)" in msg:
        return "The backend is not authorized to call the Vertex endpoint."
    if "timeout" in msg:
        return "The model request timed out."
    if "vertex ai error (400)" in msg or "invalid" in msg:
        return "The request payload was rejected by the model endpoint."
    if "cannot connect" in msg:
        return "The backend cannot reach the model endpoint."
    return "The model request failed unexpectedly."


async def analyze_uploaded_record(
    *,
    record_type: str,
    title: Optional[str],
    extracted_text: Optional[str],
    image_base64: Optional[str] = None
) -> dict[str, Any]:
    """
    Analyze an uploaded medical record using the same medical model as doctor chat.

    Returns:
        JSON-serializable dict to store in medical_records.analysis_result
    """
    safe_title = (title or "Untitled record").strip()
    extracted = (extracted_text or "").strip()
    if len(extracted) > 12000:
        extracted = extracted[:12000]
    request_id = uuid.uuid4().hex[:8]

    timestamp = datetime.now(timezone.utc).isoformat()
    base_result = {
        "model": settings.medical_model,
        "record_type": record_type,
        "generated_at": timestamp,
        "request_id": request_id,
    }

    logger.info(
        "[upload-analysis] start id=%s provider=%s model=%s record_type=%s title=%s text_len=%s has_image=%s",
        request_id,
        settings.llm_provider,
        settings.medical_model,
        record_type,
        safe_title[:120],
        len(extracted),
        bool(image_base64),
    )

    if not extracted and not image_base64:
        logger.warning("[upload-analysis] skipped: no OCR text and no image payload")
        return {
            **base_result,
            "status": "skipped",
            "summary": "No extractable content found for AI analysis.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": ["No OCR text or image content was available."],
        }

    prompt = f"""Analyze the uploaded medical record and return concise clinical insights.

Record metadata:
- record_type: {record_type}
- title: {safe_title}

Extracted text (OCR):
{extracted or "No OCR text available."}

Return JSON with this exact schema:
{{
  "summary": "short clinical summary",
  "key_findings": ["finding 1", "finding 2"],
  "clinical_significance": "why this matters clinically",
  "recommended_follow_up": ["follow-up action 1", "follow-up action 2"],
  "urgency": "low|medium|high",
  "confidence": "low|medium|high",
  "limitations": ["known uncertainty or missing data"]
}}

Rules:
- Use Vietnamese for user-facing fields.
- Keep summary under 120 words.
- Keep key_findings and recommended_follow_up concise and actionable.
- If data is limited, state that clearly in limitations.
- Return valid JSON only.
"""

    model_available = await llm_client.check_model_available(settings.medical_model)
    if not model_available:
        logger.error(
            "[upload-analysis] model unavailable id=%s provider=%s model=%s",
            request_id,
            settings.llm_provider,
            settings.medical_model
        )
        return {
            **base_result,
            "status": "error",
            "summary": "AI analysis model is unavailable on this server.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": [f"Model not available: {settings.medical_model}"],
        }

    images = [image_base64] if image_base64 else None

    try:
        raw = ""
        multimodal_error: Optional[str] = None

        if images:
            try:
                raw = await llm_client.generate(
                    model=settings.medical_model,
                    prompt=prompt,
                    system=UPLOAD_ANALYSIS_SYSTEM,
                    images=images,
                    stream=False,
                    num_predict=768,
                )
                logger.info(
                    "[upload-analysis] multimodal ok id=%s response_len=%s",
                    request_id,
                    len(raw or ""),
                )
            except Exception as exc:
                multimodal_error = _sanitize_text(str(exc) or repr(exc), max_len=500)
                logger.exception(
                    "[upload-analysis] multimodal failed id=%s provider=%s model=%s image_len=%s; falling back to text-only",
                    request_id,
                    settings.llm_provider,
                    settings.medical_model,
                    len(image_base64 or ""),
                )
        else:
            raw = await llm_client.generate(
                model=settings.medical_model,
                prompt=prompt,
                system=UPLOAD_ANALYSIS_SYSTEM,
                images=None,
                stream=False,
                num_predict=768,
            )
            logger.info(
                "[upload-analysis] text-only primary ok id=%s response_len=%s",
                request_id,
                len(raw or ""),
            )

        # Retry text-only if multimodal call returned empty/garbled payload.
        if not raw or len(raw.strip()) < 10:
            logger.warning(
                "[upload-analysis] retrying text-only id=%s reason=%s",
                request_id,
                "multimodal_error" if multimodal_error else "short_or_empty_response",
            )
            raw = await llm_client.generate(
                model=settings.medical_model,
                prompt=prompt,
                system=UPLOAD_ANALYSIS_SYSTEM,
                images=None,
                stream=False,
                num_predict=768,
            )
            logger.info(
                "[upload-analysis] text-only retry ok id=%s response_len=%s",
                request_id,
                len(raw or ""),
            )

        parsed = _extract_json_object(raw) or {}
        summary = str(parsed.get("summary") or "").strip()
        if not summary:
            summary = (raw or "").strip()[:500]
        if not summary:
            summary = "Khong the tao AI analysis."
        summary = _sanitize_text(summary, max_len=1200)

        urgency = str(parsed.get("urgency") or "").strip().lower()
        if urgency not in {"low", "medium", "high"}:
            urgency = "medium"

        confidence = str(parsed.get("confidence") or "").strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "medium"

        result: dict[str, Any] = {
            **base_result,
            "status": "completed",
            "summary": summary,
            "key_findings": _sanitize_list(_to_string_list(parsed.get("key_findings"))),
            "clinical_significance": _sanitize_text(parsed.get("clinical_significance"), max_len=1200),
            "recommended_follow_up": _sanitize_list(_to_string_list(parsed.get("recommended_follow_up"))),
            "urgency": urgency,
            "confidence": confidence,
            "limitations": _sanitize_list(_to_string_list(parsed.get("limitations")), max_item_len=500),
        }
        if multimodal_error:
            result["limitations"] = _sanitize_list(
                (result.get("limitations") or []) + [
                    "Image analysis fallback was used due to multimodal request failure.",
                ],
                max_items=6,
                max_item_len=500,
            )
        logger.info(
            "[upload-analysis] completed id=%s urgency=%s confidence=%s findings=%s follow_up=%s",
            request_id,
            result.get("urgency"),
            result.get("confidence"),
            len(result.get("key_findings") or []),
            len(result.get("recommended_follow_up") or []),
        )
        return result
    except Exception as exc:
        detail = _sanitize_text(str(exc) or repr(exc), max_len=500)
        reason = _classify_llm_error(detail)
        logger.exception(
            "[upload-analysis] failed id=%s provider=%s model=%s reason=%s error=%s has_image=%s text_len=%s title=%s",
            request_id,
            settings.llm_provider,
            settings.medical_model,
            reason,
            detail,
            bool(image_base64),
            len(extracted),
            safe_title[:120],
        )
        return {
            **base_result,
            "status": "error",
            "summary": "AI analysis is temporarily unavailable for this file.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": ["Could not complete AI analysis at this time."],
        }
    finally:
        # Keep memory usage stable after one-shot upload analysis.
        await llm_client.unload(settings.medical_model)


async def translate_vi_to_en(text: str) -> str:
    """
    Backward-compatible passthrough.
    """
    return text


async def translate_en_to_vi(text: str) -> str:
    """
    Backward-compatible passthrough.
    """
    return text


async def medical_reasoning(
    query_en: str,
    patient_context: str,
    image_base64: Optional[str] = None
) -> str:
    """
    Generate medical response using MedGemma with RAG context.
    
    Args:
        query_en: Query in English
        patient_context: Aggregated patient context from RAG
        image_base64: Optional base64-encoded medical image
        
    Returns:
        Medical response in English
    """
    prompt = f"""## Patient Context
{patient_context}

## User Query
{query_en}

Please provide a helpful, accurate medical response based on the patient's context."""

    images = [image_base64] if image_base64 else None
    
    response = await llm_client.generate(
        model=settings.medical_model,
        prompt=prompt,
        system=MEDICAL_REASONING_SYSTEM,
        images=images,
        stream=False
    )
    return response


async def process_medical_query(
    user_input_vi: str,
    patient_id: UUID,
    image_path: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """Patient query pipeline with streaming updates."""
    start_total = time.perf_counter()
    image_base64 = None
    
    # Load image if provided
    if image_path:
        path = Path(image_path)
        if path.exists():
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    # ========== STEP A: Analyze Input ==========
    yield {
        "stage": "verifying_input",
        "message": "Đang phân tích câu hỏi...",
        "progress": 0.1
    }
    start_step_a = time.perf_counter()
    query_en = user_input_vi
    elapsed_a = (time.perf_counter() - start_step_a) * 1000
    logger.info(f"[LLM] step_a_translate_input: Took {elapsed_a:.1f} ms")
    
    yield {
        "stage": "verified_input",
        "message": "Đã hiểu câu hỏi",
        "progress": 0.25,
    }

    # ========== STEP B: Medical Reasoning with RAG ==========
    yield {
        "stage": "retrieving_context",
        "message": "Đang tìm kiếm hồ sơ y tế liên quan...",
        "progress": 0.35
    }
    start_step_b_context = time.perf_counter()
    # Get patient context via RAG
    # Use original Vietnamese query for retrieval (records are primarily Vietnamese)
    patient_context = await get_patient_context(
        patient_id=patient_id,
        query=user_input_vi,
        max_chunks=10
    )
    elapsed_b_context = (time.perf_counter() - start_step_b_context) * 1000
    logger.info(f"[LLM] step_b_context: Took {elapsed_b_context:.1f} ms")
    
    yield {
        "stage": "medical_reasoning",
        "message": "Đang phân tích y khoa...",
        "progress": 0.5
    }
    
    # Medical reasoning with MedGemma
    start_step_b_reasoning = time.perf_counter()
    response_en = await medical_reasoning(
        query_en=query_en,
        patient_context=patient_context,
        image_base64=image_base64
    )
    elapsed_b_reasoning = (time.perf_counter() - start_step_b_reasoning) * 1000
    logger.info(f"[LLM] step_b_medical_reasoning: Took {elapsed_b_reasoning:.1f} ms")
    
    yield {
        "stage": "medical_reasoning",
        "message": "Hoàn thành phân tích",
        "progress": 0.7,
    }
    
    # ========== Memory Optimization: Unload MedGemma ==========
    await llm_client.unload(settings.medical_model)
    
    # ========== STEP C: Finalize Output ==========
    yield {
        "stage": "formatting_output",
        "message": "Đang chuẩn bị phản hồi...",
        "progress": 0.85
    }
    start_step_c = time.perf_counter()
    response_vi = response_en
    elapsed_c = (time.perf_counter() - start_step_c) * 1000
    logger.info(f"[LLM] step_c_translate_output: Took {elapsed_c:.1f} ms")
    
    yield {
        "stage": "complete",
        "message": "Hoàn thành",
        "progress": 1.0,
        "response": response_vi,
    }
    elapsed_total = (time.perf_counter() - start_total) * 1000
    logger.info(f"[LLM] pipeline_total: Took {elapsed_total:.1f} ms")


async def generate_clinical_summary(
    consultation_id: UUID,
    patient_id: UUID
) -> str:
    """
    Generate clinical notes summary from consultation history.
    
    Args:
        consultation_id: Consultation UUID
        patient_id: Patient UUID
        
    Returns:
        Clinical summary in Vietnamese
    """
    from app.db.database import get_supabase
    
    supabase = get_supabase()
    
    # Get consultation messages
    consultation = supabase.table("consultations").select(
        "messages, chief_complaint"
    ).eq("id", str(consultation_id)).single().execute()
    
    if not consultation.data:
        return "Không tìm thấy thông tin tư vấn."
    
    # Get patient context
    patient_context = await get_patient_context(patient_id)
    
    # Format messages for summary
    messages = consultation.data.get("messages", [])
    chief_complaint = consultation.data.get("chief_complaint", "N/A")
    
    messages_text = "\n".join([
        f"- {m.get('role', 'user')}: {m.get('content', '')}"
        for m in messages
    ])
    
    summary_prompt = f"""Based on the following consultation, generate a clinical summary for the doctor.

## Patient Context
{patient_context}

## Chief Complaint
{chief_complaint}

## Consultation Messages
{messages_text}

Generate a clinical summary including:
1. Presenting symptoms
2. Relevant medical history
3. Assessment
4. Recommendations made
5. Follow-up plan

Format the summary professionally for medical records."""

    # Generate summary with MedGemma
    summary_en = await llm_client.generate(
        model=settings.medical_model,
        prompt=summary_prompt,
        system="You are a medical documentation specialist. Generate professional clinical notes.",
        stream=False
    )
    
    await llm_client.unload(settings.medical_model)
    
    return summary_en


async def check_system_health() -> dict:
    """
    Check if all required models are available.
    
    Returns:
        Health status dict
    """
    llm_ok = await llm_client.health_check()
    provider = (settings.llm_provider or "vertex").lower()

    if not llm_ok:
        return {
            "status": "unhealthy",
            "provider": provider,
            "llm": False,
            "ollama": provider == "ollama",
            "message": f"{provider} provider is not reachable",
        }
    
    models_status = {
        "medical_model": await llm_client.check_model_available(
            settings.medical_model
        ),
        "embedding_model": await llm_client.check_model_available(
            settings.embedding_model
        )
    }
    
    all_available = all(models_status.values())
    
    return {
        "status": "healthy" if all_available else "degraded",
        "provider": provider,
        "llm": True,
        "ollama": provider == "ollama",
        "models": models_status,
        "message": "All systems operational" if all_available else "Some models missing"
    }
