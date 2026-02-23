"""
LLM Service.
"""
import asyncio
from typing import Any, AsyncGenerator, Optional
from uuid import UUID
import base64
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import uuid

from app.services.ecg_classifier_service import ecg_classifier_service
from app.services.cache import cache_response, get_cached_response, response_cache
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

UPLOAD_ANALYSIS_CACHE_TYPE = "upload_analysis:v1"


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


_PATIENT_SUMMARY_SECTION_HEADERS: list[tuple[str, str]] = [
    (r"(?:Danh sách vấn đề(?:\s*\(Problem List\))?|Problem List)", "Danh sách vấn đề (Problem List)"),
    (
        r"(?:Thuốc đang dùng(?:\s*\(Current Medications\))?|Current Medications)",
        "Thuốc đang dùng (Current Medications)",
    ),
    (r"(?:Dị ứng(?:\s*\(Allergies\))?|Allergies)", "Dị ứng (Allergies)"),
    (
        r"(?:Diễn tiến bệnh(?:\s*\(Disease Progress\))?|Disease Progress)",
        "Diễn tiến bệnh (Disease Progress)",
    ),
    (
        r"(?:Tóm tắt sinh hiệu gần nhất(?:\s*\(Recent Vitals\))?|Recent Vitals)",
        "Tóm tắt sinh hiệu gần nhất (Recent Vitals)",
    ),
    (
        r"(?:Đánh giá lâm sàng(?:\s*\(Clinical Assessment\))?|Clinical Assessment)",
        "Đánh giá lâm sàng (Clinical Assessment)",
    ),
]


def _strip_unbalanced_double_asterisks(text: str) -> str:
    """Remove broken bold markers on lines with odd '**' pairs."""
    normalized_lines: list[str] = []
    for line in text.split("\n"):
        if line.count("**") % 2 != 0:
            normalized_lines.append(line.replace("**", ""))
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


def _break_dense_lines(text: str) -> str:
    """Split long dense lines into short paragraphs for markdown rendering."""
    lines = text.split("\n")
    output: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            output.append("")
            continue

        if (
            len(line) < 170
            or line.startswith("## ")
            or re.match(r"^[-*]\s", line)
            or re.match(r"^\d+[.)]\s", line)
        ):
            output.append(line)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", line)
        paragraph: list[str] = []
        paragraph_len = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            starts_new = (
                re.match(r"^\d+[.)]\s", sentence)
                or re.match(r"^[-*]\s", sentence)
                or sentence.startswith("## ")
                or paragraph_len > 250
            )

            if starts_new and paragraph:
                output.append(" ".join(paragraph))
                output.append("")
                paragraph = []
                paragraph_len = 0

            paragraph.append(sentence)
            paragraph_len += len(sentence) + 1

        if paragraph:
            output.append(" ".join(paragraph))

    cleaned: list[str] = []
    prev_blank = False
    for line in output:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = is_blank

    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()
    return "\n".join(cleaned)


def _normalize_patient_summary_markdown(text: str) -> str:
    """
    Normalize patient profile summary markdown to avoid inline wall-of-text output.

    Handles malformed section headers, run-on numbered lists, and broken bold markers.
    """
    summary = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not summary:
        return ""

    summary = summary.replace("\u00a0", " ")
    summary = re.sub(r"[ \t]+", " ", summary)
    summary = _strip_unbalanced_double_asterisks(summary)

    # Fix missing space after sentence-ending punctuation.
    summary = re.sub(r"([.!?])(?=[A-ZÀ-Ỵa-zà-ỵ#*\\[])", r"\1 ", summary)

    # Promote known sections to consistent markdown headers.
    for pattern, canonical_header in _PATIENT_SUMMARY_SECTION_HEADERS:
        summary = re.sub(
            rf"(?:(?<=^)|(?<=[\n.!?]))\s*(?:#{1,4}\s*)?(?:\*\*)?\s*(?:{pattern})\s*(?:\*\*)?\s*:?\s*",
            f"\n\n## {canonical_header}\n",
            summary,
            flags=re.IGNORECASE,
        )

    # Ensure headers always start on their own block.
    summary = re.sub(r"(?<!\n)(##\s)", r"\n\n\1", summary)
    summary = re.sub(r"(##[^\n]+)\s*(?=(?:\d+[.)]|[-•*]))", r"\1\n", summary)

    # Normalize numbered lists (e.g., "1.[I10]" or "... điều trị.2.[E78.5]").
    summary = re.sub(r"(?<![A-Za-zÀ-Ỵa-zà-ỵ0-9])(\d+[.)])(?=\S)", r"\1 ", summary)
    summary = re.sub(r"(?<!^)(?<!\n)(\d+[.)]\s*(?=[\[A-ZÀ-Ỵa-zà-ỵ]))", r"\n\1", summary)

    # Normalize malformed inline bullets to markdown list items.
    summary = re.sub(r"([:;.!?\n])\s*\*(?=[A-ZÀ-Ỵa-zà-ỵ0-9])", r"\1\n- ", summary)
    summary = re.sub(r"([:;.!?\n])\s*([•●▪])\s*(?=[A-ZÀ-Ỵa-zà-ỵ0-9])", r"\1\n- ", summary)
    summary = re.sub(r"([:;.!?])\s*-\s+(?=[A-ZÀ-Ỵa-zà-ỵ0-9])", r"\1\n- ", summary)

    # Keep only the first occurrence of each canonical section header.
    canonical_titles = {
        re.sub(r"\s+", " ", header).strip().lower()
        for _, header in _PATIENT_SUMMARY_SECTION_HEADERS
    }
    seen_titles: set[str] = set()
    deduped_lines: list[str] = []
    for line in summary.split("\n"):
        stripped = line.strip()
        match = re.match(r"^##\s+(.+?)\s*:?\s*$", stripped, flags=re.IGNORECASE)
        if match:
            normalized_title = re.sub(r"\s+", " ", match.group(1)).strip().lower()
            if normalized_title in canonical_titles:
                if normalized_title in seen_titles:
                    continue
                seen_titles.add(normalized_title)
        deduped_lines.append(line)
    summary = "\n".join(deduped_lines)

    summary = re.sub(r"\n{3,}", "\n\n", summary).strip()
    return _break_dense_lines(summary)


def _top_scores_for_log(scores_by_class: dict[str, float], top_k: int = 3) -> list[tuple[str, float]]:
    ranked = sorted(
        ((str(label), float(score)) for label, score in scores_by_class.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[:top_k]


ECG_CLASS_DESCRIPTIONS: dict[str, str] = {
    "NORM": "Normal ECG",
    "MI": "Myocardial Infarction",
    "STTC": "ST/T Change",
    "CD": "Conduction Disturbance",
    "HYP": "Hypertrophy",
}


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


def _sha256_hex(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _build_upload_analysis_cache_key(
    *,
    record_type: str,
    title: str,
    extracted_text: str,
    image_base64: Optional[str],
) -> str:
    """
    Build deterministic cache key for upload analysis reuse.
    """
    normalized_type = (record_type or "").strip().lower()
    normalized_title = re.sub(r"\s+", " ", (title or "").strip().lower())
    text_hash = _sha256_hex(extracted_text or "")
    image_hash = _sha256_hex(image_base64 or "")
    title_hash = _sha256_hex(normalized_title)
    return (
        f"type:{normalized_type}|title:{title_hash[:16]}|"
        f"text:{text_hash[:24]}|image:{image_hash[:24]}"
    )


def _decode_cached_upload_analysis(payload: str) -> Optional[dict[str, Any]]:
    """
    Decode cached upload analysis JSON payload.
    """
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


async def _get_cached_upload_analysis(cache_key: str) -> Optional[dict[str, Any]]:
    """
    Return cached upload analysis result if present.
    """
    if not response_cache.enabled:
        return None
    cached = await get_cached_response(cache_key, query_type=UPLOAD_ANALYSIS_CACHE_TYPE)
    if not cached:
        return None
    payload, _ = cached
    return _decode_cached_upload_analysis(payload)


async def _store_upload_analysis_cache(cache_key: str, result: dict[str, Any]) -> None:
    """
    Store successful upload analysis result for reuse.
    """
    if not response_cache.enabled:
        return
    if not isinstance(result, dict):
        return
    status = str(result.get("status") or "").lower()
    if status not in {"completed", "skipped"}:
        return
    try:
        serialized = json.dumps(result, ensure_ascii=False)
    except Exception:
        return
    await cache_response(
        query=cache_key,
        response=serialized,
        query_type=UPLOAD_ANALYSIS_CACHE_TYPE,
        metadata={"kind": "upload_analysis", "status": status},
    )


async def _analyze_ecg_with_classifier(
    *,
    request_id: str,
    record_type: str,
    safe_title: str,
    image_base64: str,
    base_result: dict[str, Any],
) -> dict[str, Any]:
    """
    ECG-only analysis flow:
    image -> MedSigLIP embedding -> classifier scores -> MedGemma final analysis.
    """
    start_total = time.perf_counter()
    logger.info(
        "[upload-analysis][ecg] start id=%s model=%s image_base64_len=%s",
        request_id,
        settings.medical_model,
        len(image_base64 or ""),
    )

    model_available = await llm_client.check_model_available(settings.medical_model)
    if not model_available:
        logger.error(
            "[upload-analysis][ecg] medical model unavailable id=%s model=%s",
            request_id,
            settings.medical_model,
        )
        raise RuntimeError(f"Model not available: {settings.medical_model}")

    logger.info("[upload-analysis][ecg] classifier inference start id=%s", request_id)
    start_classifier = time.perf_counter()
    classifier_output = await ecg_classifier_service.predict_from_base64(
        image_base64,
    )
    classifier_elapsed_ms = (time.perf_counter() - start_classifier) * 1000

    classes = [str(item) for item in (classifier_output.get("classes") or [])]
    raw_scores = classifier_output.get("scores") or []
    scores = [float(item) for item in raw_scores]
    scores_by_class = {
        label: float(score)
        for label, score in zip(classes, scores)
    }
    class_description_rows = [
        {
            "class": label,
            "description": ECG_CLASS_DESCRIPTIONS.get(label, label),
        }
        for label in classes
    ]
    prediction_score_rows = [
        {
            "class": label,
            "description": ECG_CLASS_DESCRIPTIONS.get(label, label),
            "score": float(score),
        }
        for label, score in zip(classes, scores)
    ]
    logger.info(
        "[upload-analysis][ecg] classifier inference done id=%s classifier_type=%s threshold=%.3f predicted=%s top3=%s elapsed_ms=%.1f",
        request_id,
        str(classifier_output.get("classifier_type") or ""),
        float(classifier_output.get("threshold", 0.5)),
        [str(item) for item in (classifier_output.get("predicted_labels") or [])],
        _top_scores_for_log(scores_by_class, top_k=3),
        classifier_elapsed_ms,
    )

    prompt = f"""Analyze this uploaded ECG image using both:
1) The actual ECG image.
2) The classifier scores computed from MedSigLIP embedding.

Record metadata:
- record_type: {record_type}
- title: {safe_title}

ECG classifier output:
- classes (ordered): {json.dumps(classes, ensure_ascii=False)}
- class_descriptions: {json.dumps(class_description_rows, ensure_ascii=False)}
- scores (same order): {json.dumps(scores, ensure_ascii=False)}
- scores_by_class: {json.dumps(scores_by_class, ensure_ascii=False)}
- prediction_score_rows: {json.dumps(prediction_score_rows, ensure_ascii=False)}
- predicted_labels: {json.dumps(classifier_output.get("predicted_labels") or [], ensure_ascii=False)}
- threshold: {float(classifier_output.get("threshold", 0.5))}

Return JSON with this exact schema:
{{
  "summary": "short clinical summary",
  "key_findings": ["finding 1", "finding 2"],
  "clinical_significance": "why this matters clinically",
  "recommended_follow_up": ["follow-up action 1", "follow-up action 2"],
  "urgency": "low|medium|high",
  "confidence": "low|medium|high",
  "limitations": ["known uncertainty or missing data"],
  "prediction_scores": [
    {{"class": "NORM", "description": "Normal ECG", "score": 0.12}},
    {{"class": "MI", "description": "Myocardial Infarction", "score": 0.78}}
  ]
}}

Rules:
- Use Vietnamese for user-facing fields.
- Use proper Vietnamese diacritics (tone marks); do not remove accents.
- Use the image as primary evidence and classifier scores as supporting evidence.
- Do not claim a diagnosis with absolute certainty.
- Always include prediction_scores and keep class names exactly as provided.
- Keep summary under 120 words.
- Return valid JSON only.
"""

    logger.info("[upload-analysis][ecg] medgemma call start id=%s", request_id)
    start_llm = time.perf_counter()
    raw = await llm_client.generate(
        model=settings.medical_model,
        prompt=prompt,
        system=UPLOAD_ANALYSIS_SYSTEM,
        images=[image_base64],
        stream=False,
        num_predict=768,
    )
    llm_elapsed_ms = (time.perf_counter() - start_llm) * 1000
    logger.info(
        "[upload-analysis][ecg] medgemma call done id=%s response_len=%s elapsed_ms=%.1f",
        request_id,
        len(raw or ""),
        llm_elapsed_ms,
    )

    parsed = _extract_json_object(raw) or {}
    summary = str(parsed.get("summary") or "").strip()
    if not summary:
        summary = (raw or "").strip()[:500]
    if not summary:
        summary = "Không thể tạo AI analysis."
    summary = _sanitize_text(summary, max_len=1200)

    urgency = str(parsed.get("urgency") or "").strip().lower()
    if urgency not in {"low", "medium", "high"}:
        urgency = "medium"

    confidence = str(parsed.get("confidence") or "").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    total_elapsed_ms = (time.perf_counter() - start_total) * 1000
    logger.info(
        "[upload-analysis][ecg] completed id=%s urgency=%s confidence=%s findings=%s follow_up=%s elapsed_ms=%.1f",
        request_id,
        urgency,
        confidence,
        len(_sanitize_list(_to_string_list(parsed.get("key_findings")))),
        len(_sanitize_list(_to_string_list(parsed.get("recommended_follow_up")))),
        total_elapsed_ms,
    )

    return {
        **base_result,
        "status": "completed",
        "summary": summary,
        "key_findings": _sanitize_list(_to_string_list(parsed.get("key_findings"))),
        "clinical_significance": _sanitize_text(parsed.get("clinical_significance"), max_len=1200),
        "recommended_follow_up": _sanitize_list(_to_string_list(parsed.get("recommended_follow_up"))),
        "urgency": urgency,
        "confidence": confidence,
        "limitations": _sanitize_list(_to_string_list(parsed.get("limitations")), max_item_len=500),
        # Always persist classifier scores in analysis payload for downstream UI/reporting.
        "prediction_scores": prediction_score_rows,
        "ecg_classifier": {
            "classifier_type": str(classifier_output.get("classifier_type") or ""),
            "checkpoint_path": str(classifier_output.get("checkpoint_path") or ""),
            "medsiglip_model_id": str(classifier_output.get("medsiglip_model_id") or ""),
            "classes": classes,
            "scores": scores,
            "scores_by_class": scores_by_class,
            "predicted_labels": [
                str(item) for item in (classifier_output.get("predicted_labels") or [])
            ],
            "threshold": float(classifier_output.get("threshold", 0.5)),
        },
    }


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
    start_total = time.perf_counter()
    safe_title = (title or "Untitled record").strip()
    extracted = (extracted_text or "").strip()
    if len(extracted) > 12000:
        extracted = extracted[:12000]
    if (record_type or "").strip().lower() == "ecg" and image_base64:
        # ECG path is image-first; do not include OCR text in model prompt.
        extracted = ""

    cache_key = _build_upload_analysis_cache_key(
        record_type=record_type,
        title=safe_title,
        extracted_text=extracted,
        image_base64=image_base64,
    )
    cached_result = await _get_cached_upload_analysis(cache_key)
    if cached_result:
        logger.info(
            "[upload-analysis] cache hit record_type=%s title=%s text_len=%s has_image=%s",
            record_type,
            safe_title[:120],
            len(extracted),
            bool(image_base64),
        )
        return cached_result

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

    ecg_fallback_reason: Optional[str] = None
    if (record_type or "").strip().lower() == "ecg" and image_base64:
        logger.info("[upload-analysis] routing ECG request to classifier flow id=%s", request_id)
        try:
            result = await _analyze_ecg_with_classifier(
                request_id=request_id,
                record_type=record_type,
                safe_title=safe_title,
                image_base64=image_base64,
                base_result=base_result,
            )
            await _store_upload_analysis_cache(cache_key, result)
            return result
        except Exception as exc:
            ecg_fallback_reason = _sanitize_text(str(exc) or repr(exc), max_len=500)
            logger.warning(
                "[upload-analysis] ECG classifier flow failed; using default flow id=%s error=%s",
                request_id,
                ecg_fallback_reason,
            )
            logger.exception(
                "[upload-analysis][ecg] classifier workflow failed id=%s error=%s; falling back to default flow",
                request_id,
                ecg_fallback_reason,
            )

    if not extracted and not image_base64:
        logger.warning("[upload-analysis] skipped id=%s: no OCR text and no image payload", request_id)
        result = {
            **base_result,
            "status": "skipped",
            "summary": "No extractable content found for AI analysis.",
            "key_findings": [],
            "recommended_follow_up": [],
            "limitations": ["No OCR text or image content was available."],
        }
        await _store_upload_analysis_cache(cache_key, result)
        return result

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
- Use proper Vietnamese diacritics (tone marks); do not remove accents.
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
            summary = "Không thể tạo AI analysis."
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
        if ecg_fallback_reason:
            result["limitations"] = _sanitize_list(
                (result.get("limitations") or [])
                + ["ECG classifier path failed, used default upload analysis flow."],
                max_items=6,
                max_item_len=500,
            )
        if multimodal_error:
            result["limitations"] = _sanitize_list(
                (result.get("limitations") or []) + [
                    "Image analysis fallback was used due to multimodal request failure.",
                ],
                max_items=6,
                max_item_len=500,
            )
        logger.info(
            "[upload-analysis] completed id=%s urgency=%s confidence=%s findings=%s follow_up=%s used_fallback=%s elapsed_ms=%.1f",
            request_id,
            result.get("urgency"),
            result.get("confidence"),
            len(result.get("key_findings") or []),
            len(result.get("recommended_follow_up") or []),
            bool(ecg_fallback_reason),
            (time.perf_counter() - start_total) * 1000,
        )
        await _store_upload_analysis_cache(cache_key, result)
        return result
    except Exception as exc:
        detail = _sanitize_text(str(exc) or repr(exc), max_len=500)
        reason = _classify_llm_error(detail)
        logger.exception(
            "[upload-analysis] failed id=%s provider=%s model=%s reason=%s error=%s has_image=%s text_len=%s title=%s elapsed_ms=%.1f",
            request_id,
            settings.llm_provider,
            settings.medical_model,
            reason,
            detail,
            bool(image_base64),
            len(extracted),
            safe_title[:120],
            (time.perf_counter() - start_total) * 1000,
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


async def generate_patient_profile_summary(
    patient_id: UUID,
) -> dict[str, Any]:
    """
    Generate an AI clinical summary for a patient profile.

    Uses MedGemma to synthesize patient data into a structured clinical
    overview following the Problem List / POMR medical format.

    Args:
        patient_id: Patient UUID

    Returns:
        Dict with summary text, model name, and generation timestamp.
    """
    start_total = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]
    logger.info(
        "[patient-summary] start id=%s patient=%s model=%s",
        request_id,
        str(patient_id),
        settings.medical_model,
    )

    # Gather patient context via RAG (includes demographics, conditions,
    # medications, vitals, appointments, medical records).
    patient_context = await get_patient_context(patient_id)

    summary_prompt = f"""Dựa trên thông tin bệnh nhân dưới đây, hãy tạo một bản tóm tắt lâm sàng ngắn gọn theo chuẩn y khoa.

{patient_context}

Hãy viết bản tóm tắt theo đúng định dạng sau (bằng tiếng Việt, có dấu):

## Danh sách vấn đề (Problem List)
Liệt kê các bệnh lý/vấn đề sức khỏe hiện tại, kèm mã ICD-10 nếu có.
Ví dụ: 1. [E11] Đái tháo đường type 2 — Đang điều trị

## Thuốc đang dùng (Current Medications)
Liệt kê tên thuốc, liều lượng, tần suất dùng.

## Dị ứng (Allergies)
Liệt kê các dị ứng đã biết hoặc ghi "Chưa ghi nhận dị ứng" nếu không có.

## Diễn tiến bệnh (Disease Progress)
Mô tả ngắn gọn diễn tiến của các bệnh lý chính dựa trên dữ liệu sinh hiệu và lịch sử khám bệnh. Ví dụ: xu hướng đường huyết, huyết áp qua các lần đo gần đây, tuân thủ điều trị.

## Tóm tắt sinh hiệu gần nhất (Recent Vitals)
Tóm tắt các chỉ số sinh hiệu gần nhất trên một dòng.
Ví dụ: HA: 120/80 mmHg | Nhịp tim: 72 bpm | SpO₂: 98% | Đường huyết: 5.6 mmol/L

## Đánh giá lâm sàng (Clinical Assessment)
Viết 2-3 câu đánh giá tổng quát tình trạng sức khỏe của bệnh nhân, bao gồm mức độ kiểm soát bệnh và các khuyến nghị theo dõi.

QUY TẮC:
- Viết bằng tiếng Việt có dấu.
- Không dùng placeholder như [Insert...], [TODO], [N/A].
- Nếu thiếu dữ liệu, ghi rõ "Chưa có dữ liệu" thay vì bỏ trống.
- Giữ ngắn gọn, súc tích, chuyên nghiệp.
- Đây là tóm tắt cho bác sĩ xem trên hồ sơ bệnh nhân."""

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        raw = await llm_client.generate(
            model=settings.medical_model,
            prompt=summary_prompt,
            system="Bạn là trợ lý AI y khoa chuyên tạo tóm tắt lâm sàng cho bác sĩ. Viết ngắn gọn, chuyên nghiệp, bằng tiếng Việt có dấu.",
            stream=False,
            num_predict=1200,
        )
        summary_text = (raw or "").strip()
        if not summary_text:
            summary_text = "Không thể tạo tóm tắt lâm sàng. Vui lòng thử lại sau."

        # Post-process malformed markdown from model output so UI renders
        # section headers/lists consistently (similar readability as chat responses).
        summary_text = _normalize_patient_summary_markdown(summary_text)

        elapsed_ms = (time.perf_counter() - start_total) * 1000
        logger.info(
            "[patient-summary] completed id=%s patient=%s response_len=%s elapsed_ms=%.1f",
            request_id,
            str(patient_id),
            len(summary_text),
            elapsed_ms,
        )

        return {
            "summary": summary_text,
            "generated_at": timestamp,
            "model": settings.medical_model,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_total) * 1000
        logger.exception(
            "[patient-summary] failed id=%s patient=%s error=%s elapsed_ms=%.1f",
            request_id,
            str(patient_id),
            str(exc)[:300],
            elapsed_ms,
        )
        return {
            "summary": "Tạo tóm tắt lâm sàng thất bại. Vui lòng thử lại sau.",
            "generated_at": timestamp,
            "model": settings.medical_model,
            "error": str(exc)[:300],
        }
    finally:
        await llm_client.unload(settings.medical_model)


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
    
    summary_prompt = f"""Based on the following consultation, generate a structured clinical summary for medical records.

## Patient Context
{patient_context}

## Chief Complaint
{chief_complaint}

## Consultation Messages
{messages_text}

Return the summary in markdown using these top-level sections:

1. Medical History
- Chronic Conditions: include only if mentioned in consultation/context; add timeline/date when available.
- Past Surgeries: include only if mentioned; list each surgery with date and outcomes when available.
- Hospitalizations: include only if mentioned; include reason and timing.
- Medications History: include only if mentioned; include past meds and discontinuation reasons when available.
- Allergies: include only if explicitly mentioned; include trigger and reaction details.
- Psychiatric History: include only if explicitly mentioned; include diagnosis/treatment details when available.

2. Family Medical History
- Family History of Chronic Conditions: include only if explicitly mentioned.
- Family History of Mental Health Conditions: include only if explicitly mentioned.
- Family History of Genetic Conditions: include only if explicitly mentioned.

3. Immunization Records
- Vaccines Administered: include only if explicitly mentioned, with date if available.
- Vaccines Due: include only if explicitly mentioned.

4. Treatment History
- Previous Treatments: include only if mentioned; include outcomes when available.
- Physiotherapy: include only if applicable and mentioned.
- Other Relevant Treatments: include only if relevant and mentioned.

5. Treatment Records
- Regular Checkup Entries (vital signs as part of treatment records):
  - Date of examination
  - Reason for visit
  - Doctor comments on test results
  - Patient progress
  - Treatment plan
  - Doctor notes
- Medical Records (test results only): include only lab/xray/ecg/ct/mri.
  - Medical Images format:
    0) Medical file attached (if available)
    1) Doctor's test result description
    2) Doctor's final conclusion
    3) AI analysis
  - Lab Results format:
    Include a markdown table with columns: Sample Information | Test Name | Numerical Result | Unit | Flag/Status | Doctor's Notes (optional)

Rules:
- Do not use placeholders like [Enter ...].
- Do not fabricate details; include only information present in context/messages.
- Omit bullets/subsections that are not mentioned instead of writing "N/A".
- Keep wording concise and clinically clear.
"""

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
        "models": models_status,
        "message": "All systems operational" if all_available else "Some models missing"
    }
