"""
Doctor Orchestrator Graph using LangGraph.

A state machine implementation of the doctor query processing pipeline
with human-in-the-loop capabilities, input verification, and structured output.

Best Practices Applied (2025-2026):
- Retry logic with exponential backoff for LLM calls
- Circuit breaker pattern for service protection
- Fuzzy patient name matching for better accuracy
- Defensive "I don't know" responses for hallucination prevention
- Comprehensive audit logging for safety-critical decisions
"""
import base64
import json
import logging
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import AsyncGenerator, Literal, Optional, List, Tuple
from uuid import UUID

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.services.graph_state import (
    DoctorOrchestratorState,
    QueryType,
    create_initial_doctor_state,
    create_stage_message,
    PatientMatch,
    HITLRequest,
)
from app.services.llm_client import llm_client
from app.services.transformers_client import transformers_client
from app.services.rag import (
    get_patient_context,
    get_patient_record_images_base64,
)
from app.services.verification_service import (
    verify_input,
    check_response_safety,
    should_request_clarification,
    should_require_safety_review,
)
from app.services.output_formatter import format_response, format_as_plain_text
from app.services.resilience import (
    retry_async,
    RetryConfig,
    get_circuit_breaker,
    with_circuit_breaker,
    CircuitBreakerOpen,
    create_idk_response,
    detect_uncertainty_in_response,
    create_defensive_response,
    safety_audit,
)
from app.services.cache import (
    get_cached_response,
    cache_response,
    response_cache,
)
from app.db.database import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)

# Circuit breakers for external services
_llm_breaker = get_circuit_breaker("llm_doctor", failure_threshold=3, recovery_timeout=60.0)
_db_breaker = get_circuit_breaker("database_doctor", failure_threshold=5, recovery_timeout=30.0)

# Retry configuration for LLM calls
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    retryable_exceptions=(RuntimeError, TimeoutError, ConnectionError)
)


# ============================================================================
# FUZZY MATCHING UTILITIES (Vietnamese-optimized)
# ============================================================================

def normalize_vietnamese_name(name: str) -> str:
    """
    Normalize Vietnamese name for comparison.

    Removes diacritics and converts to lowercase for fuzzy matching.
    Vietnamese: Nguyễn Thị Lan → nguyen thi lan
    """
    # Lowercase and strip
    name = name.lower().strip()

    # Normalize unicode (NFD decomposes characters)
    name = unicodedata.normalize('NFD', name)

    # Remove combining diacritical marks
    name = ''.join(c for c in name if not unicodedata.combining(c))

    # Additional Vietnamese-specific replacements
    replacements = {
        'đ': 'd', 'Đ': 'D',
    }
    for old, new in replacements.items():
        name = name.replace(old, new)

    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name)

    return name


def extract_vietnamese_given_name(full_name: str) -> str:
    """
    Extract the given name (last word) from a Vietnamese full name.

    Vietnamese names: Family + Middle + Given (e.g., "Nguyễn Thị Lan" → "Lan")
    The given name is the most unique identifier.
    """
    parts = full_name.strip().split()
    return parts[-1] if parts else ""


def fuzzy_match_score(name1: str, name2: str) -> float:
    """
    Calculate fuzzy match score between two Vietnamese names.

    Uses multiple strategies for accurate Vietnamese name matching:
    1. Exact match (with diacritics)
    2. Normalized match (without diacritics)
    3. Given name match (last word - most unique in Vietnamese)
    4. SequenceMatcher for partial matches
    """
    # Normalize names (keep diacritics for exact match)
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    # 1. Exact match with diacritics
    if n1 == n2:
        return 1.0

    # Normalize without diacritics
    n1_normalized = normalize_vietnamese_name(name1)
    n2_normalized = normalize_vietnamese_name(name2)

    # 2. Exact match without diacritics
    if n1_normalized == n2_normalized:
        return 0.98

    # 3. Given name (last word) matching - critical for Vietnamese
    given1 = extract_vietnamese_given_name(n1)
    given2 = extract_vietnamese_given_name(n2)
    given1_norm = normalize_vietnamese_name(given1)
    given2_norm = normalize_vietnamese_name(given2)

    # If given names don't match, significantly penalize
    given_names_match = (given1 == given2 or given1_norm == given2_norm)

    # 4. Full substring match (one name contains the other entirely)
    if n1 in n2 or n2 in n1:
        return 0.95 if given_names_match else 0.5

    # 5. Normalized substring match
    if n1_normalized in n2_normalized or n2_normalized in n1_normalized:
        return 0.92 if given_names_match else 0.45

    # 6. SequenceMatcher for fuzzy matching on normalized names
    base_score = SequenceMatcher(None, n1_normalized, n2_normalized).ratio()

    # Heavily penalize if given names don't match (they should be unique)
    if not given_names_match:
        base_score *= 0.4  # Reduce to 40% if given names differ

    return base_score


def find_best_patient_matches(
    search_name: str,
    patients: List[dict],
    min_score: float = 0.8
) -> List[Tuple[dict, float]]:
    """
    Find best matching patients using Vietnamese-optimized fuzzy matching.

    Args:
        search_name: Name to search for (Vietnamese or partial)
        patients: List of patient records from database
        min_score: Minimum match score threshold (default 0.8 for stricter matching)

    Returns:
        List of (patient, score) tuples sorted by score descending
    """
    matches = []
    exact_match = None

    search_normalized = normalize_vietnamese_name(search_name)
    search_given = normalize_vietnamese_name(extract_vietnamese_given_name(search_name))

    for patient in patients:
        full_name = patient.get("full_name", "")
        patient_normalized = normalize_vietnamese_name(full_name)
        patient_given = normalize_vietnamese_name(extract_vietnamese_given_name(full_name))

        # Check for exact match first (prioritize)
        if search_normalized == patient_normalized:
            exact_match = (patient, 1.0)
            continue

        score = fuzzy_match_score(search_name, full_name)

        # Only include if score meets threshold
        if score >= min_score:
            matches.append((patient, score))

    # If exact match found, return only that
    if exact_match:
        return [exact_match]

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    # If multiple matches have very close scores (within 0.1),
    # they're considered ambiguous - keep all for HITL
    if len(matches) > 1:
        top_score = matches[0][1]
        # Keep matches within 0.1 of top score for HITL review
        matches = [(p, s) for p, s in matches if s >= top_score - 0.1]

    return matches


# ============================================================================
# IMAGE ATTACHMENT GATING
# ============================================================================

_EXPLICIT_IMAGE_REQUEST_KEYWORDS: tuple[str, ...] = (
    "show image",
    "show images",
    "display image",
    "display images",
    "attach image",
    "include image",
    "send image",
    "xem hinh",
    "xem anh",
    "hien thi hinh",
    "hien thi anh",
    "dinh kem hinh",
    "dinh kem anh",
    "gui hinh",
    "gui anh",
    "cho toi xem hinh",
    "cho toi xem anh",
)

_IMAGE_RELEVANCE_KEYWORDS: tuple[str, ...] = (
    "xray",
    "x ray",
    "x quang",
    "radiograph",
    "ct",
    "mri",
    "ultrasound",
    "sieu am",
    "ecg",
    "ekg",
    "dicom",
    "imaging",
    "scan",
    "hinh anh",
    "hinh x quang",
    "phim x quang",
)


def _normalize_query_text(text: str) -> str:
    """
    Normalize query text for robust keyword matching across Vietnamese/English.
    """
    normalized = unicodedata.normalize("NFD", (text or "").lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("đ", "d")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _query_contains_keyword(normalized_query: str, keyword: str) -> bool:
    """
    Keyword matcher with boundary checks for short tokens (for example: "ct").
    """
    if not keyword:
        return False
    if " " in keyword:
        return keyword in normalized_query
    if len(keyword) <= 3:
        return re.search(rf"\b{re.escape(keyword)}\b", normalized_query) is not None
    return keyword in normalized_query


def _should_include_record_images(state: DoctorOrchestratorState) -> Tuple[bool, str]:
    """
    Decide whether patient record images should be fetched and attached.

    Images are included only if the doctor explicitly asks for them
    or the query is imaging-related.
    """
    if state.get("image_base64"):
        return True, "user_uploaded_image"

    if state.get("query_type") == QueryType.IMAGE_ANALYSIS:
        return True, "query_type_image_analysis"

    normalized_query = _normalize_query_text(
        f"{state.get('query_vi', '')} {state.get('query_en', '')}"
    )
    if not normalized_query:
        return False, "empty_query"

    if any(_query_contains_keyword(normalized_query, keyword) for keyword in _EXPLICIT_IMAGE_REQUEST_KEYWORDS):
        return True, "explicit_image_request"

    if any(_query_contains_keyword(normalized_query, keyword) for keyword in _IMAGE_RELEVANCE_KEYWORDS):
        return True, "imaging_related_query"

    return False, "not_requested_or_relevant"


def _llm_hitl_enabled(state: DoctorOrchestratorState) -> bool:
    """Whether LLM-dependent HITL checks are enabled for this request."""
    return bool(state.get("enable_llm_hitl", state.get("enable_hitl", True)))


def _patient_confirmation_hitl_enabled(state: DoctorOrchestratorState) -> bool:
    """Whether non-LLM patient confirmation HITL is enabled for this request."""
    return bool(state.get("enable_patient_confirmation_hitl", state.get("enable_hitl", True)))


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

async def translate_input_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Translate Vietnamese input to English.
    
    Uses EnviT5 for translation.
    """
    logger.info(f"[Graph] translate_input: {state['query_vi'][:50]}...")
    start_time = time.perf_counter()
    try:
        if settings.doctor_graph_use_translation_model:
            query_en = await transformers_client.translate_vi_to_en(state["query_vi"])
            stage_message = "Hoàn thành dịch sang tiếng Anh"
            logger.info("[Graph] translate_input: Translation model enabled")
        else:
            # Temporary fast path for direct MedGemma testing without translation model.
            query_en = state["query_vi"]
            stage_message = "Bỏ qua dịch, dùng truy vấn gốc"
            logger.info("[Graph] translate_input: Translation model disabled, using original query directly")

        # Load image if provided
        image_base64 = None
        if state.get("image_path"):
            path = Path(state["image_path"])
            if path.exists():
                with open(path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "query_en": query_en,
            "image_base64": image_base64,
            "current_stage": "translated_input",
            "progress": 0.15,
            "stage_messages": [create_stage_message(
                "translating_input",
                stage_message,
                0.15,
                translation=query_en
            )]
        }
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[Graph] translate_input: Took {elapsed_ms:.1f} ms")


async def verify_input_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Verify input query for clarity and appropriateness.
    
    Uses Gemma 2B for lightweight verification.
    May trigger HITL interrupt if clarification needed.
    """
    logger.info("[Graph] verify_input: Checking query clarity...")
    start_time = time.perf_counter()
    try:
        verification = await verify_input(state["query_en"])

        result = {
            "verification_result": verification,
            "input_confidence": verification["confidence"],
            "current_stage": "verified_input",
            "progress": 0.25,
            "stage_messages": [create_stage_message(
                "verifying_input",
                f"Kiểm tra độ rõ ràng: {verification['confidence']:.0%}",
                0.25
            )]
        }
        # Check if HITL is enabled for this request and clarification is needed
        if _llm_hitl_enabled(state) and should_request_clarification(verification):
            logger.info("[Graph] verify_input: Requesting clarification via HITL")

            # Create HITL request
            hitl_request = HITLRequest(
                type="clarification_needed",
                message="Câu hỏi cần được làm rõ",
                details={
                    "original_query": state["query_vi"],
                    "issues": verification["issues"],
                    "suggestions": verification["suggested_rewrites"],
                },
                options=verification["suggested_rewrites"] if verification["suggested_rewrites"] else None
            )

            # Interrupt for human input
            clarified = interrupt(hitl_request)

            if clarified:
                # Human provided clarification
                result["query_vi"] = clarified.get("query", state["query_vi"])
                result["human_approved_input"] = True
                # Re-translate only when translation model is enabled.
                if result["query_vi"] != state["query_vi"]:
                    if settings.doctor_graph_use_translation_model:
                        result["query_en"] = await transformers_client.translate_vi_to_en(result["query_vi"])
                    else:
                        result["query_en"] = result["query_vi"]

        return result
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[Graph] verify_input: Took {elapsed_ms:.1f} ms")


async def extract_patients_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Extract patient mentions from query.

    Uses MedGemma to identify patient names with retry logic.
    """
    logger.info("[Graph] extract_patients: Identifying patients...")
    start_time = time.perf_counter()

    extraction_prompt = f"Query: {state['query_en']}"
    extraction_system = """Extract patient names from the query.
Output ONLY a valid JSON array of names: ["Name1", "Name2"] or [] if no patients mentioned.
Do not include any other text.

IMPORTANT: If the query is a general medical question NOT about a specific patient, return [].
Examples:
- "What are metformin side effects?" → []
- "How is patient Bình doing?" → ["Bình"]
- "Any patients need attention today?" → []
- "Tình trạng của bệnh nhân Trần Thị Bình?" → ["Trần Thị Bình"]
- "Thuốc hạ huyết áp nào phổ biến nhất?" → []"""

    mentioned_names = []

    try:
        async def _extraction_call():
            return await llm_client.generate(
                model=settings.medical_model,
                prompt=extraction_prompt,
                system=extraction_system,
                stream=False,
                num_predict=128
            )

        response = await with_circuit_breaker(
            _llm_breaker,
            retry_async,
            _extraction_call,
            config=LLM_RETRY_CONFIG,
            operation_name="extract_patients"
        )

        # Parse response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        names = json.loads(clean)
        mentioned_names = names if isinstance(names, list) else []

    except CircuitBreakerOpen:
        logger.error("[Graph] extract_patients: Circuit breaker open")
        mentioned_names = []

    except json.JSONDecodeError as e:
        logger.warning(f"[Graph] extract_patients: JSON parse failed: {e}")
        mentioned_names = []

    except Exception as e:
        logger.warning(f"[Graph] extract_patients: Failed: {e}")
        mentioned_names = []

    # Determine query type
    if mentioned_names:
        query_type = QueryType.PATIENT_SPECIFIC
    elif any(kw in state["query_en"].lower() for kw in ["all patients", "overview", "summary", "urgent", "tất cả"]):
        query_type = QueryType.AGGREGATE
    elif state.get("image_base64"):
        query_type = QueryType.IMAGE_ANALYSIS
    else:
        query_type = QueryType.GENERAL

    logger.info(f"[Graph] extract_patients: Found {len(mentioned_names)} patients, type={query_type}")

    result = {
        "mentioned_patient_names": mentioned_names,
        "query_type": query_type,
        "current_stage": "extracted_patients",
        "progress": 0.35,
        "stage_messages": [create_stage_message(
            "extracting_patients",
            f"Tìm thấy {len(mentioned_names)} bệnh nhân được nhắc đến",
            0.35,
            patient_names=mentioned_names
        )]
    }
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] extract_patients: Took {elapsed_ms:.1f} ms")
    return result


async def resolve_patients_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Resolve patient names to database records.

    Uses fuzzy matching for better accuracy with typos and partial names.
    May trigger HITL for confirmation if multiple matches.
    """
    logger.info("[Graph] resolve_patients: Looking up patients...")
    start_time = time.perf_counter()

    if not state["mentioned_patient_names"]:
        result = {
            "matched_patients": [],
            "current_stage": "resolved_patients",
            "progress": 0.40,
            "stage_messages": [create_stage_message(
                "resolving_patients",
                "Không có bệnh nhân cụ thể được nhắc đến",
                0.40
            )]
        }
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[Graph] resolve_patients: Took {elapsed_ms:.1f} ms")
        return result

    try:
        supabase = get_supabase()
        matches: List[PatientMatch] = []
        ambiguous_matches: List[dict] = []

        for name in state["mentioned_patient_names"]:
            # First, try exact and partial matches via database
            result = supabase.table("patients").select(
                "id, full_name, primary_diagnosis, date_of_birth, gender"
            ).ilike(
                "full_name", f"%{name}%"
            ).limit(10).execute()

            if result.data:
                # Apply Vietnamese-optimized fuzzy matching to database results
                # Threshold 0.8 = strict matching to prevent false positives
                fuzzy_results = find_best_patient_matches(name, result.data, min_score=0.8)

                for patient, score in fuzzy_results:
                    match = PatientMatch(
                        id=patient["id"],
                        name=patient["full_name"],
                        primary_diagnosis=patient.get("primary_diagnosis"),
                        match_confidence=score
                    )
                    matches.append(match)

                    # Track ambiguous matches for HITL (stricter: < 0.95)
                    if score < 0.95:
                        ambiguous_matches.append({
                            "name": patient["full_name"],
                            "score": score,
                            "search_term": name
                        })
            else:
                # No database match - try broader search with fuzzy
                logger.info(f"[Graph] resolve_patients: No exact match for '{name}', trying broader search")

                # Get more patients for fuzzy matching
                all_patients = supabase.table("patients").select(
                    "id, full_name, primary_diagnosis"
                ).limit(50).execute()

                if all_patients.data:
                    # Threshold 0.7 for broader search (still stricter than before)
                    fuzzy_results = find_best_patient_matches(name, all_patients.data, min_score=0.7)
                    for patient, score in fuzzy_results[:3]:  # Top 3 fuzzy matches
                        matches.append(PatientMatch(
                            id=patient["id"],
                            name=patient["full_name"],
                            primary_diagnosis=patient.get("primary_diagnosis"),
                            match_confidence=score
                        ))
                        ambiguous_matches.append({
                            "name": patient["full_name"],
                            "score": score,
                            "search_term": name,
                            "fuzzy_match": True
                        })

        # Deduplicate, keeping highest confidence
        unique: dict[str, PatientMatch] = {}
        for m in matches:
            if m["id"] not in unique or m["match_confidence"] > unique[m["id"]]["match_confidence"]:
                unique[m["id"]] = m

        matched_patients = list(unique.values())

        # Log patient resolution for audit
        safety_audit.log_decision(
            event_type="patient_resolution",
            query=state["query_en"],
            decision=f"resolved_{len(matched_patients)}_patients",
            confidence=min([m["match_confidence"] for m in matched_patients]) if matched_patients else 0.0,
            risk_factors=[f"ambiguous:{a['name']}" for a in ambiguous_matches],
            human_review_required=bool(ambiguous_matches),
        )

        # HITL: Confirm if ambiguous, multiple matches, or any low-confidence match
        # More aggressive triggering to prevent wrong patient selection
        has_low_confidence = any(m["match_confidence"] < 0.95 for m in matched_patients)
        has_multiple_matches = len(matched_patients) > 1
        needs_confirmation = ambiguous_matches or has_low_confidence or has_multiple_matches

        if _patient_confirmation_hitl_enabled(state) and needs_confirmation:
            logger.info(f"[Graph] resolve_patients: Requesting patient confirmation "
                       f"(ambiguous={bool(ambiguous_matches)}, low_conf={has_low_confidence}, multiple={has_multiple_matches})")

            # Provide helpful context for confirmation
            confirmation_details = {
                "matches": matched_patients,
                "ambiguous": ambiguous_matches,
                "search_terms": state["mentioned_patient_names"]
            }

            confirmed = interrupt(HITLRequest(
                type="patient_confirmation",
                message="Vui lòng xác nhận bệnh nhân được đề cập. Một số tên có thể không chính xác hoàn toàn.",
                details=confirmation_details,
                options=[f"{m['name']} (độ tin cậy: {m['match_confidence']:.0%})" for m in matched_patients]
            ))

            if confirmed:
                confirmed_ids = confirmed.get("patient_ids", [m["id"] for m in matched_patients])
                matched_patients = [m for m in matched_patients if m["id"] in confirmed_ids]

        logger.info(f"[Graph] resolve_patients: Resolved {len(matched_patients)} patients")

        result = {
            "matched_patients": matched_patients,
            "current_stage": "resolved_patients",
            "progress": 0.45,
            "stage_messages": [create_stage_message(
                "resolving_patients",
                f"Tìm thấy {len(matched_patients)} hồ sơ bệnh nhân",
                0.45,
                mentioned_patients=[{"id": m["id"], "name": m["name"], "confidence": m["match_confidence"]} for m in matched_patients]
            )]
        }
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[Graph] resolve_patients: Took {elapsed_ms:.1f} ms")
        return result

    except Exception as e:
        logger.error(f"[Graph] resolve_patients: Database error: {e}")
        result = {
            "matched_patients": [],
            "current_stage": "resolved_patients",
            "progress": 0.45,
            "errors": [f"Không thể tra cứu bệnh nhân: {str(e)}"],
            "stage_messages": [create_stage_message(
                "resolving_patients",
                "Lỗi tra cứu bệnh nhân - vui lòng thử lại",
                0.45
            )]
        }
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[Graph] resolve_patients: Took {elapsed_ms:.1f} ms")
        return result


async def get_context_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Retrieve patient context via RAG.

    Gets relevant medical records for identified patients.
    Also fetches and encodes patient record images for LLM analysis.
    """
    logger.info("[Graph] get_context: Retrieving medical context...")
    start_time = time.perf_counter()

    record_attachments: List[dict] = []
    patient_record_images_base64: List[str] = []
    include_record_images, image_gate_reason = _should_include_record_images(state)
    logger.info(
        "[Graph] get_context: image_gate include=%s reason=%s query_type=%s",
        include_record_images,
        image_gate_reason,
        state.get("query_type"),
    )

    if state["query_type"] == QueryType.AGGREGATE:
        # Get overview of all patients
        context = await _get_aggregate_overview()
    elif state["matched_patients"]:
        # Get context for specific patients
        context_parts = []
        for patient in state["matched_patients"]:
            patient_context = await get_patient_context(
                patient_id=UUID(patient["id"]),
                # Use original Vietnamese query for better retrieval
                query=state["query_vi"],
                max_chunks=5
            )
            context_parts.append(patient_context)
            context_parts.append("\n---\n")

            if include_record_images:
                # Fetch actual patient record images for LLM analysis + UI attachments
                images_b64, attachments = await get_patient_record_images_base64(
                    patient_id=UUID(patient["id"]),
                    limit=2
                )
                if images_b64:
                    patient_record_images_base64.extend(images_b64)
                if attachments:
                    record_attachments.extend(attachments)

        context = "\n".join(context_parts)
        if not include_record_images:
            logger.info(
                "[Graph] get_context: Skipped record image fetch (reason=%s)",
                image_gate_reason,
            )
        logger.info(
            f"[Graph] get_context: Loaded {len(patient_record_images_base64)} "
            "patient record images for analysis"
        )
    else:
        context = "No specific patient context available."

    # Unload medical model to free memory for next step
    await llm_client.unload(settings.medical_model)

    result = {
        "patient_context": context,
        "record_attachments": record_attachments[:6],
        "patient_record_images_base64": patient_record_images_base64[:4],  # Limit to 4 images
        "current_stage": "retrieved_context",
        "progress": 0.55,
        "stage_messages": [create_stage_message(
            "retrieving_context",
            f"Hoàn thành tổng hợp thông tin y tế ({len(patient_record_images_base64)} hình ảnh)",
            0.55
        )]
    }
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] get_context: Took {elapsed_ms:.1f} ms")
    return result

def _add_paragraph_breaks(text: str) -> str:
    """
    Add line breaks to dense Vietnamese text for better readability.

    Strategy: split into sentences, then insert blank lines at topic
    boundaries (bullet points, questions, transitional phrases, and
    after long runs of text).

    Args:
        text: Dense text without proper formatting

    Returns:
        Text with paragraph breaks inserted
    """
    if not text or len(text) < 100:
        return text

    # If the text already has reasonable formatting, leave it alone
    if text.count("\n\n") >= 3:
        return text

    # ---- Step 1: Normalize inline markdown and list markers ----
    # Handle inline markdown headers: "...ổn định.## Phân tích" → split before ##
    text = re.sub(r'(?<!\n)(#{1,4}\s)', r'\n\n\1', text)
    # Handle inline dash lists: "...huyết áp.- Điều trị:" → split before dash
    text = re.sub(r'([.!?])\s*-\s+', r'\1\n\n- ', text)
    # Handle "...thương.•Suy hô hấp" → split before bullet
    text = re.sub(r'([.!?])\s*([•●▪]\s*)', r'\1\n\n\2', text)
    # Handle "...thương.1. Suy hô hấp" → split before numbered list
    text = re.sub(r'([.!?])\s*(\d+[.)]\s)', r'\1\n\n\2', text)

    # ---- Step 2: Split into lines (preserve any existing breaks) ----
    lines = text.split("\n")
    result_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            result_lines.append("")
            continue

        # If the line is short enough, keep as-is
        if len(line) < 150:
            result_lines.append(line)
            continue

        # ---- Step 3: Split dense line into sentences ----
        # Split on sentence-ending punctuation followed by a space or bullet
        sentences = re.split(r'(?<=[.!?])\s+', line)

        current_paragraph: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Detect if this sentence starts a new topic
            is_new_topic = False

            # Bullet point or numbered list
            if re.match(r'^[•●▪\-]\s', sentence) or re.match(r'^\d+[.)]\s', sentence):
                is_new_topic = True

            # Question sentence
            elif sentence.endswith("?"):
                is_new_topic = True

            # Starts with a transitional/topic phrase
            elif re.match(
                r'^(Tuy nhiên|Ngoài ra|Vậy|Tóm lại|Điều này|Cách tiếp cận|'
                r'Lưu ý|Ví dụ|Về cơ bản|Nói chung|Cần lưu ý|Cần theo dõi|'
                r'Những điều|Việc điều trị|Do đó|Vì vậy|Bên cạnh đó|'
                r'However|In addition|Therefore|For example|In summary)',
                sentence, re.IGNORECASE
            ):
                is_new_topic = True

            # Current paragraph is getting long (>250 chars)
            elif current_length > 250:
                is_new_topic = True

            if is_new_topic and current_paragraph:
                # Flush current paragraph
                result_lines.append(" ".join(current_paragraph))
                result_lines.append("")  # blank line = paragraph break
                current_paragraph = []
                current_length = 0

            current_paragraph.append(sentence)
            current_length += len(sentence) + 1

        # Flush remaining sentences
        if current_paragraph:
            result_lines.append(" ".join(current_paragraph))

    # ---- Step 4: Clean up multiple blank lines ----
    cleaned: list[str] = []
    prev_blank = False
    for line in result_lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue  # skip double blanks
        cleaned.append(line)
        prev_blank = is_blank

    # Remove trailing blank line
    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()

    return "\n".join(cleaned)


def _build_system_prompt(query_type: QueryType) -> str:
    """
    Build a query-type-aware system prompt for MedGemma.

    Returns different prompts based on query type to produce natural,
    context-appropriate responses directly in Vietnamese.
    """
    # Shared safety guidelines for all query types
    safety_guidelines = """QUY TẮC AN TOÀN:
1. CHỈ cung cấp thông tin dựa trên dữ liệu được cung cấp
2. KHÔNG BAO GIỜ bịa đặt thông tin bệnh nhân, kết quả xét nghiệm, hoặc tiền sử bệnh
3. KHÔNG sử dụng placeholder như [Insert...], [TODO], [N/A]
4. Nếu thiếu thông tin quan trọng, nói rõ "Không đủ dữ liệu"
5. Nếu có hình ảnh y tế, phân tích kỹ và mô tả những gì quan sát được
6. Trả lời hoàn toàn bằng tiếng Việt"""

    if query_type == QueryType.GENERAL:
        return f"""You are a medical AI assistant supporting doctors.

The doctor is asking a general medical question (NOT about a specific patient).
Provide a natural, clear, and helpful response. DO NOT use patient assessment structure.
Respond as a professional medical discussion between colleagues.

FORMATTING REQUIREMENTS:
- Use **bold** for section headers or important medical terms
- Break content into SHORT paragraphs separated by blank lines
- Use bullet lists (•) when listing multiple items
- DO NOT write one continuous block of text

LANGUAGE: Respond entirely in Vietnamese.

{safety_guidelines}"""

    elif query_type == QueryType.PATIENT_SPECIFIC:
        return f"""Bạn là trợ lý AI y khoa hỗ trợ bác sĩ quản lý bệnh nhân.

Bác sĩ đang hỏi về bệnh nhân cụ thể. Hãy cung cấp đánh giá có cấu trúc.
CHỈ bao gồm các phần liên quan đến câu hỏi (không cần tất cả):

## Đánh giá
Tình trạng hiện tại dựa trên dữ liệu có sẵn

## Phân tích
Kết quả chính từ hồ sơ và hình ảnh

## Đề xuất
Hành động được đề xuất dựa trên bằng chứng

## Cảnh báo
Các vấn đề cần chú ý ngay (nếu có)

{safety_guidelines}"""

    elif query_type == QueryType.AGGREGATE:
        return f"""Bạn là trợ lý AI y khoa hỗ trợ bác sĩ.

Bác sĩ đang yêu cầu tổng quan về nhiều bệnh nhân.
Hãy tóm tắt ngắn gọn, ưu tiên các trường hợp khẩn cấp lên đầu.
Sử dụng định dạng danh sách dễ đọc.

{safety_guidelines}"""

    elif query_type == QueryType.IMAGE_ANALYSIS:
        return f"""Bạn là trợ lý AI y khoa chuyên phân tích hình ảnh y tế.

Hãy phân tích kỹ các hình ảnh được cung cấp. Mô tả:
- Những gì quan sát được trong hình ảnh
- Các phát hiện bất thường (nếu có)
- Đề xuất xét nghiệm hoặc theo dõi thêm

Nếu có thông tin bệnh nhân, kết hợp với phân tích hình ảnh.

{safety_guidelines}"""

    else:
        # Fallback
        return f"""Bạn là trợ lý AI y khoa hỗ trợ bác sĩ.
Hãy trả lời câu hỏi một cách chính xác và hữu ích.

{safety_guidelines}"""


async def medical_reasoning_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Generate medical response using MedGemma.

    Core reasoning step with patient context, retry logic, and defensive responses.
    Supports analysis of both user-uploaded images and patient record images.
    """
    logger.info("[Graph] medical_reasoning: Generating response...")
    start_time = time.perf_counter()

    # Check if we have sufficient context
    has_context = bool(state['patient_context'] and state['patient_context'].strip() != "No specific patient context available.")

    # Combine all available images for analysis
    all_images: List[str] = []

    # Add user-uploaded image first (if any)
    if state.get("image_base64"):
        all_images.append(state["image_base64"])

    # Add patient record images from database
    if state.get("patient_record_images_base64"):
        all_images.extend(state["patient_record_images_base64"])

    has_images = len(all_images) > 0
    logger.info(f"[Graph] medical_reasoning: {len(all_images)} images available for analysis")

    # Build prompt with image context
    image_context = ""
    if has_images:
        image_context = f"\n\n## Hình ảnh y tế (Medical Images)\n{len(all_images)} image(s) attached for analysis. Please analyze these images as part of your assessment."

    reasoning_prompt = f"""## Ngữ cảnh bệnh nhân (Patient Context)
{state['patient_context']}{image_context}

## Câu hỏi của bác sĩ (Doctor's Query)
{state['query_en']}
"""

    # Build query-type-aware system prompt
    query_type = state.get("query_type", QueryType.GENERAL)
    system_prompt = _build_system_prompt(query_type)

    try:
        async def _reasoning_call():
            return await llm_client.generate(
                model=settings.medical_model,
                prompt=reasoning_prompt,
                system=system_prompt,
                images=all_images if all_images else None,
                stream=False,
                num_predict=max(int(settings.doctor_reasoning_max_tokens), 128)
            )

        response_en = await with_circuit_breaker(
            _llm_breaker,
            retry_async,
            _reasoning_call,
            config=LLM_RETRY_CONFIG,
            operation_name="medical_reasoning"
        )

        # Check for uncertainty in response and add defensive disclaimer if needed
        if detect_uncertainty_in_response(response_en, language="en"):
            logger.info("[Graph] medical_reasoning: Detected uncertainty - adding context warning")

        # Add context availability disclaimer
        if not has_context and query_type != QueryType.GENERAL:
            response_en = f"""⚠️ Thông tin bệnh nhân hạn chế. Vui lòng đối chiếu với hồ sơ bệnh án đầy đủ.

---

{response_en}"""
        
        # Add paragraph breaks for all query types (model often returns wall of text)
        response_en = _add_paragraph_breaks(response_en)
        logger.info("[Graph] medical_reasoning: Applied paragraph formatting to response")

        logger.info(f"[Graph] medical_reasoning: Generated {len(response_en)} chars")

    except CircuitBreakerOpen:
        logger.error("[Graph] medical_reasoning: Circuit breaker open")
        response_en = create_idk_response(
            reason="Medical AI service temporarily unavailable",
            original_query=state['query_en'],
            language="en",
            suggestions=[
                "Please try again in a few minutes",
                "Review patient records directly",
                "Consult with colleagues if urgent"
            ]
        )

    except Exception as e:
        logger.error(f"[Graph] medical_reasoning: Failed: {e}")
        response_en = create_idk_response(
            reason=f"Error processing medical query: {str(e)[:100]}",
            original_query=state['query_en'],
            language="en",
            suggestions=[
                "Try rephrasing your question",
                "Check if patient context was loaded correctly",
                "Contact system administrator if issue persists"
            ]
        )

    result = {
        "reasoning_en": response_en,
        "current_stage": "reasoned",
        "progress": 0.70,
        "stage_messages": [create_stage_message(
            "medical_reasoning",
            "Hoàn thành phân tích y khoa",
            0.70,
            response_en=response_en[:200] + "..." if len(response_en) > 200 else response_en
        )]
    }
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] medical_reasoning: Took {elapsed_ms:.1f} ms")
    return result


async def safety_check_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Check response safety.

    May trigger HITL for high-risk responses.
    Includes comprehensive audit logging for all safety decisions.
    """
    logger.info("[Graph] safety_check: Reviewing response safety...")
    start_time = time.perf_counter()

    # Unload MedGemma, load verification model
    try:
        await llm_client.unload(settings.medical_model)
    except Exception as e:
        logger.warning(f"[Graph] safety_check: Failed to unload model: {e}")

    safety_score, risk_factors, needs_review = await check_response_safety(state["reasoning_en"])

    # Determine if human review is required
    requires_human_review = should_require_safety_review(safety_score, risk_factors)

    # Log safety decision for audit trail
    safety_audit.log_decision(
        event_type="safety_check",
        query=state["query_en"],
        decision=f"score_{safety_score:.2f}",
        confidence=safety_score,
        risk_factors=risk_factors,
        patient_id=state["matched_patients"][0]["id"] if state.get("matched_patients") else None,
        human_review_required=requires_human_review,
        response_preview=state["reasoning_en"][:300]
    )

    result = {
        "safety_score": safety_score,
        "safety_issues": risk_factors,
        "current_stage": "safety_checked",
        "progress": 0.80,
        "stage_messages": [create_stage_message(
            "safety_check",
            f"Kiểm tra an toàn: {safety_score:.0%}" + (" ⚠️" if risk_factors else " ✓"),
            0.80,
            safety_score=safety_score,
            risk_factors=risk_factors
        )]
    }

    # HITL: Request approval for risky responses
    if _llm_hitl_enabled(state) and requires_human_review:
        logger.info(f"[Graph] safety_check: Requesting human approval (score={safety_score:.2f}, risks={risk_factors})")

        # Provide detailed context for reviewer
        review_message = "Phản hồi này cần được xác nhận vì:\n"
        if safety_score < 0.5:
            review_message += "• Điểm an toàn thấp\n"
        for factor in risk_factors[:3]:  # Show top 3 risks
            review_message += f"• {factor}\n"

        approved = interrupt(HITLRequest(
            type="approval_required",
            message=review_message,
            details={
                "response_preview": state["reasoning_en"][:500],
                "risk_factors": risk_factors,
                "safety_score": safety_score,
                "query": state["query_vi"]
            },
            options=["Phê duyệt (Approve)", "Từ chối (Reject)", "Chỉnh sửa (Edit)"]
        ))

        if approved:
            action = approved.get("action", "approve").lower()

            # Log human decision
            safety_audit.log_decision(
                event_type="human_review",
                query=state["query_en"],
                decision=action,
                confidence=safety_score,
                risk_factors=risk_factors,
                human_review_required=True,
                human_approved=(action == "approve" or action == "phê duyệt"),
            )

            if action in ["reject", "từ chối"]:
                result["errors"] = ["Phản hồi đã bị từ chối bởi người đánh giá"]
                result["human_approved_output"] = False
            elif action in ["edit", "chỉnh sửa"] and approved.get("edited_response"):
                result["reasoning_en"] = approved["edited_response"]
                result["human_approved_output"] = True
            else:
                result["human_approved_output"] = True

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] safety_check: Took {elapsed_ms:.1f} ms")
    return result


async def format_output_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Format the response for display.
    
    Creates structured sections from raw response.
    """
    logger.info("[Graph] format_output: Structuring response...")
    start_time = time.perf_counter()
    
    formatted = format_response(
        response_text=state["reasoning_en"],
        language="vi",  # MedGemma 27B responds directly in Vietnamese
        confidence=state["input_confidence"] * state["safety_score"],
        sources=["patient_records"]
    )
    
    result = {
        "formatted_response": formatted,
        "current_stage": "formatted",
        "progress": 0.85,
        "stage_messages": [create_stage_message(
            "formatting_output",
            "Đang định dạng phản hồi",
            0.85
        )]
    }
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] format_output: Took {elapsed_ms:.1f} ms")
    return result


async def translate_output_node(state: DoctorOrchestratorState) -> dict:
    """
    Node: Finalize output.
    
    MedGemma 27B responds directly in Vietnamese, so no translation needed.
    This node now acts as a pass-through that packages the final response.
    """
    logger.info("[Graph] translate_output: Packaging Vietnamese response (no translation needed)...")
    start_time = time.perf_counter()
    
    # MedGemma 27B already responds in Vietnamese — pass through directly
    response_vi = state["reasoning_en"]  # Already Vietnamese despite the field name
    
    # Formatted sections are already in Vietnamese too
    formatted = state.get("formatted_response")
    if formatted:
        formatted = formatted.copy()
        formatted["raw_text"] = response_vi
    
    attachments = state.get("record_attachments", [])
    result = {
        "response_vi": response_vi,
        "formatted_response": formatted,
        "current_stage": "complete",
        "progress": 1.0,
        "stage_messages": [create_stage_message(
            "complete",
            "Hoàn thành",
            1.0,
            response=response_vi,
            attachments=attachments
        )]
    }
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"[Graph] translate_output: Took {elapsed_ms:.1f} ms")
    return result


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_after_translation(state: DoctorOrchestratorState) -> Literal["verify_input", "extract_patients"]:
    """
    Route after translation.

    Fast-path optimization:
    - When LLM-HITL is disabled, skip expensive verification call.
    """
    if not _llm_hitl_enabled(state):
        return "extract_patients"
    return "verify_input"


def route_after_verification(state: DoctorOrchestratorState) -> Literal["extract_patients", END]:
    """Route after verification: continue or abort if invalid."""
    if state.get("errors"):
        return END
    return "extract_patients"


def route_after_reasoning(state: DoctorOrchestratorState) -> Literal["safety_check", "format_output"]:
    """
    Route after medical reasoning.

    Fast-path optimization:
    - When LLM-HITL is disabled, skip expensive safety-check LLM call.
    """
    if not _llm_hitl_enabled(state):
        return "format_output"
    return "safety_check"


def route_after_safety(state: DoctorOrchestratorState) -> Literal["format_output", "medical_reasoning", END]:
    """Route after safety check: continue, regenerate, or abort."""
    if state.get("errors"):
        return END
    if state.get("human_approved_output") is False:
        # Rejected - try regenerating
        return "medical_reasoning"
    return "format_output"


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_doctor_graph():
    """
    Build the doctor orchestrator graph.

    Returns:
        Compiled graph ready for execution with checkpointing
    """
    # Create graph with state schema
    builder = StateGraph(DoctorOrchestratorState)
    
    # Add nodes
    builder.add_node("translate_input", translate_input_node)
    builder.add_node("verify_input", verify_input_node)
    builder.add_node("extract_patients", extract_patients_node)
    builder.add_node("resolve_patients", resolve_patients_node)
    builder.add_node("get_context", get_context_node)
    builder.add_node("medical_reasoning", medical_reasoning_node)
    builder.add_node("safety_check", safety_check_node)
    builder.add_node("format_output", format_output_node)
    builder.add_node("translate_output", translate_output_node)
    
    # Add edges
    builder.add_edge(START, "translate_input")
    builder.add_conditional_edges(
        "translate_input",
        route_after_translation,
        ["verify_input", "extract_patients"]
    )
    builder.add_conditional_edges(
        "verify_input",
        route_after_verification,
        ["extract_patients", END]
    )
    builder.add_edge("extract_patients", "resolve_patients")
    builder.add_edge("resolve_patients", "get_context")
    builder.add_edge("get_context", "medical_reasoning")
    builder.add_conditional_edges(
        "medical_reasoning",
        route_after_reasoning,
        ["safety_check", "format_output"]
    )
    builder.add_conditional_edges(
        "safety_check",
        route_after_safety,
        ["format_output", "medical_reasoning", END]
    )
    builder.add_edge("format_output", "translate_output")
    builder.add_edge("translate_output", END)
    
    # Compile with checkpointer for HITL support
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph


# ============================================================================
# PUBLIC API
# ============================================================================

# Global graph instance
_doctor_graph = None


def get_doctor_graph():
    """Get or create the doctor orchestrator graph singleton."""
    global _doctor_graph
    if _doctor_graph is None:
        _doctor_graph = build_doctor_graph()
    return _doctor_graph


# ============================================================================
# VISUALIZATION UTILITIES (LangChain Graph API)
# ============================================================================

def get_doctor_graph_mermaid(
    *,
    with_styles: bool = True,
    wrap_label_n_words: int = 9,
    curve_style=None,
    node_colors=None,
    frontmatter_config: Optional[dict] = None,
) -> str:
    """
    Return a Mermaid diagram for the doctor graph.

    Args:
        with_styles: Include default styles in Mermaid output.
        wrap_label_n_words: Wrap long labels every N words.
        curve_style: Optional CurveStyle enum from langchain_core.runnables.graph.
        node_colors: Optional NodeStyles from langchain_core.runnables.graph.
        frontmatter_config: Optional Mermaid frontmatter config dict.
    """
    graph = get_doctor_graph()
    graph_view = graph.get_graph()

    draw_kwargs = {
        "with_styles": with_styles,
        "wrap_label_n_words": wrap_label_n_words,
    }
    if curve_style is not None:
        draw_kwargs["curve_style"] = curve_style
    if node_colors is not None:
        draw_kwargs["node_colors"] = node_colors
    if frontmatter_config is not None:
        draw_kwargs["frontmatter_config"] = frontmatter_config

    return graph_view.draw_mermaid(**draw_kwargs)


def save_doctor_graph_png(
    output_path: Path,
    *,
    with_styles: bool = True,
    wrap_label_n_words: int = 9,
    curve_style=None,
    node_colors=None,
    frontmatter_config: Optional[dict] = None,
    draw_method=None,
    background_color: str = "white",
    padding: int = 10,
) -> Path:
    """
    Render the doctor graph to a PNG file using Mermaid rendering.

    Args:
        output_path: Where to write the PNG.
        with_styles: Include default styles in Mermaid output.
        wrap_label_n_words: Wrap long labels every N words.
        curve_style: Optional CurveStyle enum from langchain_core.runnables.graph.
        node_colors: Optional NodeStyles from langchain_core.runnables.graph.
        frontmatter_config: Optional Mermaid frontmatter config dict.
        draw_method: Optional MermaidDrawMethod enum (API/PYPPETEER).
        background_color: PNG background color.
        padding: PNG padding in pixels.
    """
    graph = get_doctor_graph()
    graph_view = graph.get_graph()

    draw_kwargs = {
        "output_file_path": str(output_path),
        "with_styles": with_styles,
        "wrap_label_n_words": wrap_label_n_words,
        "background_color": background_color,
        "padding": padding,
    }
    if curve_style is not None:
        draw_kwargs["curve_style"] = curve_style
    if node_colors is not None:
        draw_kwargs["node_colors"] = node_colors
    if frontmatter_config is not None:
        draw_kwargs["frontmatter_config"] = frontmatter_config
    if draw_method is not None:
        draw_kwargs["draw_method"] = draw_method

    graph_view.draw_mermaid_png(**draw_kwargs)
    return output_path


async def process_doctor_query_graph(
    query_vi: str,
    image_path: Optional[str] = None,
    thread_id: Optional[str] = None,
    enable_hitl: bool = True,
    enable_llm_hitl: Optional[bool] = None,
    enable_patient_confirmation_hitl: Optional[bool] = None,
) -> AsyncGenerator[dict, None]:
    """
    Process a doctor query using the LangGraph orchestrator.
    
    Yields stage updates for real-time UI feedback.
    
    Args:
        query_vi: Vietnamese query from doctor
        image_path: Optional path to medical image
        thread_id: Optional thread ID for state persistence
        enable_hitl: Legacy global HITL toggle (used as fallback defaults)
        enable_llm_hitl: Enable LLM-based HITL checks (verify_input + safety_check)
        enable_patient_confirmation_hitl: Enable non-LLM patient confirmation HITL
        
    Yields:
        Stage update dictionaries
    """
    graph = get_doctor_graph()
    llm_hitl = enable_hitl if enable_llm_hitl is None else enable_llm_hitl
    patient_confirmation_hitl = (
        enable_hitl
        if enable_patient_confirmation_hitl is None
        else enable_patient_confirmation_hitl
    )
    cache_mode = f"hitl:llm:{int(bool(llm_hitl))}:pc:{int(bool(patient_confirmation_hitl))}"

    # Check cache first (only for queries without images)
    if not image_path and response_cache.enabled:
        cached = await get_cached_response(query_vi, query_type=cache_mode)
        if cached:
            response_vi, response_en = cached
            logger.info(f"[Graph] Cache HIT for query: {query_vi[:50]}...")
            yield create_stage_message("starting", "Đang tải kết quả...", 0.0)
            yield {
                "stage": "complete",
                "message": "Hoàn thành (từ bộ nhớ đệm)",
                "progress": 1.0,
                "response": response_vi,
                "response_en": response_en,
                "from_cache": True
            }
            return

    # Create initial state
    initial_state = create_initial_doctor_state(
        query_vi,
        image_path,
        enable_hitl=enable_hitl,
        enable_llm_hitl=llm_hitl,
        enable_patient_confirmation_hitl=patient_confirmation_hitl,
    )
    if not llm_hitl:
        logger.info("[Graph] LLM fast path enabled: skipping verify_input and safety_check nodes")

    # Config for checkpointing
    config = {"configurable": {"thread_id": thread_id or "default"}}

    # Initial progress
    yield create_stage_message(
        "starting",
        "Đang bắt đầu xử lý...",
        0.0
    )

    start_total = time.perf_counter()
    try:
        # Run graph and stream updates
        async for event in graph.astream(initial_state, config=config):
            # Extract node name and state updates
            for node_name, node_output in event.items():
                if node_name == "__interrupt__":
                    # HITL interrupt - yield the request
                    yield {
                        "stage": "hitl_required",
                        "hitl_request": node_output[0].value if node_output else None
                    }
                    continue
                
                # Yield stage messages from node output
                if isinstance(node_output, dict):
                    stage_messages = node_output.get("stage_messages", [])
                    for msg in stage_messages:
                        yield msg
                    
                    # Also yield current progress
                    if "progress" in node_output:
                        yield {
                            "stage": node_output.get("current_stage", "processing"),
                            "progress": node_output["progress"]
                        }
        
        # Get final state
        final_state = graph.get_state(config).values

        response_vi = final_state.get("response_vi", "")
        response_en = final_state.get("reasoning_en", "")

        # Cache successful response (only for non-image queries)
        if response_vi and not image_path and response_cache.enabled:
            patient_ids = [m["id"] for m in final_state.get("matched_patients", [])]
            await cache_response(
                query=query_vi,
                response=response_vi,
                response_en=response_en,
                patient_ids=patient_ids if patient_ids else None,
                query_type=cache_mode,
                metadata={
                    "safety_score": final_state.get("safety_score"),
                    "patient_count": len(patient_ids),
                    "graph_query_type": str(final_state.get("query_type", "general")),
                }
            )
            logger.info(f"[Graph] Cached response for query: {query_vi[:50]}...")

        # Yield completion with full response
        yield {
            "stage": "complete",
            "message": "Hoàn thành",
            "progress": 1.0,
            "response": response_vi,
            "response_en": response_en,
            "formatted_response": final_state.get("formatted_response"),
            "mentioned_patients": [
                {"id": m["id"], "name": m["name"]}
                for m in final_state.get("matched_patients", [])
            ],
            "safety_score": final_state.get("safety_score"),
            "attachments": final_state.get("record_attachments", []),
        }
        
    except CircuitBreakerOpen as e:
        logger.error(f"[Graph] Circuit breaker open: {e}")
        yield {
            "stage": "error",
            "message": "Hệ thống đang tạm thời quá tải. Vui lòng thử lại sau ít phút.",
            "progress": 0.0,
            "error": str(e)
        }

    except Exception as e:
        logger.exception(f"[Graph] Error processing query: {e}")

        # Provide user-friendly Vietnamese error messages
        error_message = "Đã xảy ra lỗi khi xử lý yêu cầu. "
        if "timeout" in str(e).lower():
            error_message += "Hệ thống đang phản hồi chậm. Vui lòng thử lại."
        elif "connection" in str(e).lower():
            error_message += "Không thể kết nối đến dịch vụ AI. Vui lòng kiểm tra kết nối."
        elif "memory" in str(e).lower():
            error_message += "Hệ thống đang quá tải. Vui lòng thử lại sau."
        else:
            error_message += "Vui lòng thử lại hoặc liên hệ hỗ trợ kỹ thuật."

        yield {
            "stage": "error",
            "message": error_message,
            "progress": 0.0,
            "error": str(e)
        }
    finally:
        elapsed_ms = (time.perf_counter() - start_total) * 1000
        logger.info(f"[Graph] pipeline_total: Took {elapsed_ms:.1f} ms")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_aggregate_overview() -> str:
    """Get overview of all active patients."""
    supabase = get_supabase()
    
    result = supabase.table("patients").select(
        "id, full_name, primary_diagnosis, triage_priority, "
        "profile_status, last_checkup_date"
    ).eq("profile_status", "active").order(
        "triage_priority", desc=True
    ).limit(50).execute()
    
    if not result.data:
        return "No active patients found."
    
    overview_parts = ["## Active Patients Overview\n"]
    
    priority_groups = {"urgent": [], "high": [], "medium": [], "low": [], None: []}
    
    for patient in result.data:
        priority = patient.get("triage_priority")
        if priority in priority_groups:
            priority_groups[priority].append(patient)
        else:
            priority_groups[None].append(patient)
    
    for priority in ["urgent", "high", "medium", "low"]:
        patients = priority_groups.get(priority, [])
        if patients:
            overview_parts.append(f"\n### Priority: {priority.upper()}")
            for p in patients:
                overview_parts.append(
                    f"- **{p.get('full_name', 'N/A')}**: "
                    f"{p.get('primary_diagnosis', 'No diagnosis')} "
                    f"(Last checkup: {p.get('last_checkup_date', 'N/A')})"
                )
    
    return "\n".join(overview_parts)
