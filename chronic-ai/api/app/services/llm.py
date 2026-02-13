"""
Translation Sandwich Pipeline (LLM Service).

Implements the three-step translation process:
1. Vietnamese → English (VinAI Translate)
2. Medical Reasoning (MedGemma 4B) with RAG context
3. English → Vietnamese (VinAI Translate)

VinAI Translate models are kept persistent for performance.
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

from app.services.ollama_client import ollama_client
from app.services.transformers_client import transformers_client
from app.services.rag import get_patient_context
from app.config import settings

logger = logging.getLogger(__name__)

# System prompts for translation
VI_TO_EN_SYSTEM = """You are a professional medical translator. 
Translate the following Vietnamese text to English accurately.
Preserve all medical terminology and context.
Output ONLY the English translation, nothing else."""

EN_TO_VI_SYSTEM = """You are a professional medical translator specializing in Vietnamese healthcare.
Translate the following English text to Vietnamese.

CRITICAL GUIDELINES:
- Use PROPER Vietnamese medical terminology - do NOT translate technical terms word-by-word
- Common medical terms to use correctly:
  * "opacity" / "opacities" → "vùng mờ" or "đám mờ" (NOT "quang khuông" or similar)
  * "radiolucency" → "vùng sáng" or "độ xuyên thấu"
  * "patchy" → "dạng đám" or "không đều"
  * "hilar" → "rốn phổi"
  * "infiltrate" → "thâm nhiễm"
  * "consolidation" → "đông đặc"
  * "effusion" → "tràn dịch"
  * "nodule" → "nốt"
  * "mass" → "khối"
  * "cardiomegaly" → "tim to"
- Remove all markdown formatting (**, *, #, etc.) - output plain text only
- Use proper Vietnamese punctuation and grammar
- The translation should be natural and easy to understand for Vietnamese readers
- For unclear technical terms, keep the English term in parentheses

Output ONLY the Vietnamese translation, nothing else."""

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

    timestamp = datetime.now(timezone.utc).isoformat()
    base_result = {
        "model": settings.medical_model,
        "record_type": record_type,
        "generated_at": timestamp,
    }

    logger.info(
        "[upload-analysis] start record_type=%s title=%s text_len=%s has_image=%s",
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

    model_available = await ollama_client.check_model_available(settings.medical_model)
    if not model_available:
        logger.error(
            "[upload-analysis] model unavailable: %s",
            settings.medical_model
        )
        return {
            **base_result,
            "status": "error",
            "summary": "AI analysis model is not available on this server.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": [f"Model not available: {settings.medical_model}"],
        }

    images = [image_base64] if image_base64 else None

    try:
        raw = await ollama_client.generate(
            model=settings.medical_model,
            prompt=prompt,
            system=UPLOAD_ANALYSIS_SYSTEM,
            images=images,
            stream=False,
            num_predict=768,
        )
        logger.info("[upload-analysis] primary-generate ok response_len=%s", len(raw or ""))

        # Retry text-only if multimodal call returned empty/garbled payload.
        if not raw or len(raw.strip()) < 10:
            logger.warning("[upload-analysis] primary response too short; retrying text-only")
            raw = await ollama_client.generate(
                model=settings.medical_model,
                prompt=prompt,
                system=UPLOAD_ANALYSIS_SYSTEM,
                images=None,
                stream=False,
                num_predict=768,
            )
            logger.info("[upload-analysis] retry-generate ok response_len=%s", len(raw or ""))

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
        logger.info(
            "[upload-analysis] completed urgency=%s confidence=%s findings=%s follow_up=%s",
            result.get("urgency"),
            result.get("confidence"),
            len(result.get("key_findings") or []),
            len(result.get("recommended_follow_up") or []),
        )
        return result
    except Exception as exc:
        logger.exception("[upload-analysis] failed: %s", exc)
        return {
            **base_result,
            "status": "error",
            "summary": "AI analysis is temporarily unavailable for this file.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": [_sanitize_text(str(exc), max_len=500)],
        }
    finally:
        # Keep memory usage stable after one-shot upload analysis.
        await ollama_client.unload(settings.medical_model)


async def translate_vi_to_en(text: str) -> str:
    """
    Translate Vietnamese to English using VinAI Translate.

    Uses vinai/vinai-translate-vi2en model with caching and batch optimization.

    Args:
        text: Vietnamese text to translate

    Returns:
        English translation
    """
    return await transformers_client.translate_vi_to_en(text)


async def translate_en_to_vi(text: str) -> str:
    """
    Translate English to Vietnamese using VinAI Translate.

    Uses vinai/vinai-translate-en2vi model with structure preservation.

    Args:
        text: English text to translate

    Returns:
        Vietnamese translation
    """
    return await transformers_client.translate_en_to_vi(text)


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
    
    response = await ollama_client.generate(
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
    """
    Full Translation Sandwich Pipeline with streaming.
    
    Steps:
        A. Vietnamese → English (VietAI EnviT5)
        B. Medical Reasoning (MedGemma 4B) + RAG Context
        C. English → Vietnamese (VietAI EnviT5)
    
    Yields:
        Dict with stage info and content for real-time UI updates
        
    Args:
        user_input_vi: User's question in Vietnamese
        patient_id: Patient UUID for context retrieval
        image_path: Optional path to medical image
    """
    start_total = time.perf_counter()
    image_base64 = None
    
    # Load image if provided
    if image_path:
        path = Path(image_path)
        if path.exists():
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    # ========== STEP A: Vietnamese → English ==========
    yield {
        "stage": "translating_input",
        "message": "Đang dịch câu hỏi...",
        "progress": 0.1
    }
    start_step_a = time.perf_counter()
    query_en = await translate_vi_to_en(user_input_vi)
    elapsed_a = (time.perf_counter() - start_step_a) * 1000
    logger.info(f"[LLM] step_a_translate_input: Took {elapsed_a:.1f} ms")
    
    yield {
        "stage": "translating_input",
        "message": "Hoàn thành dịch sang tiếng Anh",
        "progress": 0.25,
        "translation": query_en
    }

    # Note: Translation models are kept persistent for performance

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
        "response_en": response_en
    }
    
    # ========== Memory Optimization: Unload MedGemma ==========
    await ollama_client.unload(settings.medical_model)
    
    # ========== STEP C: English → Vietnamese ==========
    yield {
        "stage": "translating_output",
        "message": "Đang dịch phản hồi sang tiếng Việt...",
        "progress": 0.85
    }
    start_step_c = time.perf_counter()
    response_vi = await translate_en_to_vi(response_en)
    elapsed_c = (time.perf_counter() - start_step_c) * 1000
    logger.info(f"[LLM] step_c_translate_output: Took {elapsed_c:.1f} ms")
    
    yield {
        "stage": "complete",
        "message": "Hoàn thành",
        "progress": 1.0,
        "response": response_vi,
        "response_en": response_en  # Include English for doctor reference
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

    # Translate prompt to English
    prompt_en = await translate_vi_to_en(summary_prompt)

    # Note: Translation models are kept persistent for performance

    # Generate summary with MedGemma
    summary_en = await ollama_client.generate(
        model=settings.medical_model,
        prompt=prompt_en,
        system="You are a medical documentation specialist. Generate professional clinical notes.",
        stream=False
    )
    
    await ollama_client.unload(settings.medical_model)
    
    # Translate back to Vietnamese
    summary_vi = await translate_en_to_vi(summary_en)
    
    return summary_vi


async def check_system_health() -> dict:
    """
    Check if all required models are available.
    
    Returns:
        Health status dict
    """
    ollama_ok = await ollama_client.health_check()
    
    if not ollama_ok:
        return {
            "status": "unhealthy",
            "ollama": False,
            "message": "Ollama is not running"
        }
    
    models_status = {
        "vinai_vi2en": transformers_client.is_vi2en_loaded(),
        "vinai_en2vi": transformers_client.is_en2vi_loaded(),
        "medical_model": await ollama_client.check_model_available(
            settings.medical_model
        ),
        "embedding_model": await ollama_client.check_model_available(
            settings.embedding_model
        )
    }
    
    all_available = all(models_status.values())
    
    return {
        "status": "healthy" if all_available else "degraded",
        "ollama": True,
        "models": models_status,
        "message": "All systems operational" if all_available else "Some models missing"
    }
