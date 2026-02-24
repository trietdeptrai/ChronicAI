"""
Patient Chat Graph using LangGraph.

A simplified, safety-focused graph for patient interactions.
Includes symptom triage, escalation for urgent cases, and strict safety checks.

Best Practices Applied (2025-2026):
- Proper checkpointing with MemorySaver for state persistence
- Correct final state retrieval using graph.get_state(config)
- Retry logic for LLM calls
- Defensive "I don't know" responses
- Circuit breaker protection for external services
"""
import base64
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Literal, Optional, Tuple
from uuid import UUID
import re
import unicodedata

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.services.graph_state import (
    PatientChatState,
    create_stage_message,
    FormattedResponse,
    VerificationResult,
    HITLRequest
)
from app.services.llm_client import llm_client
from app.services.json_utils import strip_markdown_code_fence
from app.services.rag import get_patient_context
from app.services.verification_service import (
    verify_input,
    check_response_safety,
    should_require_safety_review
)
from app.services.output_formatter import format_response, get_urgency_indicator
from app.services.doctor_graph import _add_paragraph_breaks
from app.services.resilience import (
    retry_async,
    RetryConfig,
    get_circuit_breaker,
    with_circuit_breaker,
    CircuitBreakerOpen,
    create_idk_response,
    detect_uncertainty_in_response,
    safety_audit,
)
from app.db.database import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)

# Circuit breakers for external services
_llm_breaker = get_circuit_breaker("llm_patient", failure_threshold=3, recovery_timeout=60.0)
_db_breaker = get_circuit_breaker("database_patient", failure_threshold=5, recovery_timeout=30.0)

# Retry configuration for LLM calls
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=max(int(settings.llm_retry_max_attempts), 1),
    base_delay=max(float(settings.llm_retry_base_delay), 0.0),
    max_delay=10.0,
    retryable_exceptions=(RuntimeError, TimeoutError, ConnectionError)
)

# Safety-first override for self-harm/suicide content.
# If any of these appear in the patient query, we always escalate.
SELF_HARM_EMERGENCY_KEYWORDS = [
    "suicide",
    "suicidal",
    "kill myself",
    "end my life",
    "self-harm",
    "hurt myself",
    "tự tử",
    "ý định tự tử",
    "muốn chết",
    "không muốn sống",
    "tự hại",
    "hại bản thân",
]

# Deterministic out-of-scope guardrail for patient chat
PATIENT_NON_MEDICAL_REQUEST_KEYWORDS = [
    "bai tho",
    "lam tho",
    "viet tho",
    "poem",
    "poetry",
    "lyrics",
    "bai hat",
    "viet rap",
    "joke",
    "funny",
    "truyen",
    "ke chuyen",
    "story",
    "essay",
    "viet email",
    "email",
    "viet code",
    "lap trinh",
    "thoi tiet",
    "weather",
    "gia co phieu",
    "stock",
    "bong da",
    "football",
]

PATIENT_MEDICAL_SCOPE_REFUSAL_VI = (
    "Tôi chỉ hỗ trợ các câu hỏi về sức khỏe và y tế.\n\n"
    "Vui lòng mô tả triệu chứng, thuốc đang dùng, hoặc câu hỏi liên quan đến tình trạng sức khỏe của bạn."
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _contains_self_harm_emergency(text: str) -> bool:
    """Return True when text contains self-harm/suicide emergency signals."""
    if not text:
        return False
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in SELF_HARM_EMERGENCY_KEYWORDS)


def _normalize_scope_text(text: str) -> str:
    """Normalize text for robust keyword matching."""
    normalized = unicodedata.normalize("NFD", (text or "").lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("đ", "d")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _scope_contains_keyword(normalized_query: str, keyword: str) -> bool:
    """Boundary-safe keyword check."""
    if not keyword:
        return False
    return re.search(rf"\b{re.escape(keyword)}\b", normalized_query) is not None


def _is_out_of_scope_patient_query(query: str) -> Tuple[bool, str]:
    """
    Return whether a patient query is outside medical scope.

    Blocks explicit non-medical intent deterministically (for example: poem requests).
    """
    normalized_query = _normalize_scope_text(query)
    if not normalized_query:
        return True, "empty_query"

    if any(_scope_contains_keyword(normalized_query, kw) for kw in PATIENT_NON_MEDICAL_REQUEST_KEYWORDS):
        return True, "non_medical_intent"

    return False, "in_scope"

def create_initial_patient_state(
    patient_id: str,
    query_vi: str,
    image_path: Optional[str] = None
) -> PatientChatState:
    """Create initial state for patient chat."""
    return PatientChatState(
        # Input
        patient_id=patient_id,
        query_vi=query_vi,
        query_en="",
        image_path=image_path,
        scope_guard_blocked=False,
        scope_guard_reason=None,
        
        # Context
        patient_profile={},
        medical_history="",
        
        # Processing
        verification_result=None,
        reasoning_en="",
        
        # Safety
        urgency_level="low",
        escalation_needed=False,
        escalation_reason=None,
        
        # Output
        response_vi="",
        formatted_response=None,
        
        # Meta
        current_stage="initialized",
        progress=0.0,
        errors=[]
    )


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

async def translate_patient_input_node(state: PatientChatState) -> dict:
    """Node: Normalize patient input."""
    logger.info(f"[PatientGraph] translate_input: {state['query_vi'][:50]}...")
    query_en = state["query_vi"]

    is_out_of_scope, scope_reason = _is_out_of_scope_patient_query(query_en)
    if is_out_of_scope:
        logger.info(f"[PatientGraph] translate_input: blocked by scope guard ({scope_reason})")
        return {
            "query_en": query_en,
            "scope_guard_blocked": True,
            "scope_guard_reason": scope_reason,
            "reasoning_en": PATIENT_MEDICAL_SCOPE_REFUSAL_VI,
            "current_stage": "scope_blocked",
            "progress": 0.75,
        }

    return {
        "query_en": query_en,
        "scope_guard_blocked": False,
        "scope_guard_reason": None,
        "current_stage": "translated_input",
        "progress": 0.15
    }


async def verify_patient_input_node(state: PatientChatState) -> dict:
    """
    Node: Verify patient input.
    
    For patients, we primarily check for clarity.
    If unclear, we might ask for clarification automatically in the response
    rather than a complex HITL interrupt, to keep chat fluid.
    """
    logger.info("[PatientGraph] verify_input: Checking clarity...")
    
    verification = await verify_input(state["query_en"])

    result = {
        "verification_result": verification,
        "current_stage": "verified_input",
        "progress": 0.25
    }
    # Defense in depth: re-check scope after verification stage.
    final_query = state.get("query_en", "")
    is_out_of_scope, scope_reason = _is_out_of_scope_patient_query(final_query)
    if is_out_of_scope:
        logger.info(f"[PatientGraph] verify_input: blocked by scope guard ({scope_reason})")
        result.update({
            "scope_guard_blocked": True,
            "scope_guard_reason": scope_reason,
            "reasoning_en": PATIENT_MEDICAL_SCOPE_REFUSAL_VI,
            "current_stage": "scope_blocked",
            "progress": 0.75,
        })
    else:
        result["scope_guard_blocked"] = False
        result["scope_guard_reason"] = None

    return result


async def get_patient_history_node(state: PatientChatState) -> dict:
    """Node: Retrieve patient profile and history."""
    logger.info(f"[PatientGraph] get_history: Loading profile for {state['patient_id']}...")
    
    supabase = get_supabase()
    
    # Get profile
    patient_result = supabase.table("patients").select("*").eq(
        "id", state["patient_id"]
    ).single().execute()
    
    if not patient_result.data:
        raise ValueError(f"Patient {state['patient_id']} not found")
        
    patient = patient_result.data
    
    # Get relevant medical context via RAG
    context = await get_patient_context(
        patient_id=UUID(state["patient_id"]),
        # Use original Vietnamese query for better retrieval
        query=state["query_vi"],
        max_chunks=3  # Less context for patient to reduce latency
    )
    
    return {
        "patient_profile": patient,
        "medical_history": context,
        "current_stage": "retrieved_history",
        "progress": 0.40
    }


async def symptom_triage_node(state: PatientChatState) -> dict:
    """
    Node: Triage symptoms to detect emergencies.

    Uses MedGemma to classify urgency with retry logic and circuit breaker.
    """
    logger.info("[PatientGraph] symptom_triage: Assessing urgency...")

    triage_system = """You are a medical triage assistant. Analyze the patient query for urgency.

Classify as:
1. EMERGENCY: Life-threatening (chest pain, stroke signs, heavy bleeding, difficulty breathing, loss of consciousness) OR ANY suicide/self-harm intent -> requires immediate hospital/emergency support
2. HIGH: Severe symptoms needing doctor visit in 24h (high fever, severe pain, significant bleeding)
3. MEDIUM: Bothersome symptoms needing appointment (persistent symptoms, moderate discomfort)
4. LOW: General questions or mild symptoms (health inquiries, mild symptoms)

IMPORTANT: When in doubt, err on the side of caution and classify higher.
Return the "reason" field in Vietnamese.

Output ONLY valid JSON: {"urgency": "level", "reason": "brief reason", "confidence": 0.0-1.0}"""

    triage_prompt = f"""Patient Profile: {state['patient_profile'].get('age')}yo {state['patient_profile'].get('gender')}
Conditions: {state['patient_profile'].get('chronic_conditions')}
Query: {state['query_en']}"""

    query_text = f"{state.get('query_vi', '')} {state.get('query_en', '')}"

    # Hard safety override: never allow self-harm/suicide intent to be downgraded by the model.
    if _contains_self_harm_emergency(query_text):
        urgency = "emergency"
        reason = "Phát hiện dấu hiệu tự gây hại hoặc ý định tự tử"
        confidence = 1.0
        safety_audit.log_decision(
            event_type="symptom_triage",
            query=state.get("query_en", ""),
            decision=urgency,
            confidence=confidence,
            risk_factors=[reason],
            patient_id=state.get("patient_id"),
            human_review_required=True,
        )
        return {
            "urgency_level": urgency,
            "escalation_needed": True,
            "escalation_reason": reason,
            "current_stage": "triaged",
            "progress": 0.50
        }

    urgency = "medium"  # Safe default
    reason = "Chưa đủ thông tin để đánh giá chính xác"
    confidence = 0.5

    try:
        # Use circuit breaker and retry logic
        async def _triage_call():
            return await llm_client.generate(
                model=settings.medical_model,
                prompt=triage_prompt,
                system=triage_system,
                stream=False,
                num_predict=128
            )

        response = await with_circuit_breaker(
            _llm_breaker,
            retry_async,
            _triage_call,
            config=LLM_RETRY_CONFIG,
            operation_name="symptom_triage"
        )

        clean = strip_markdown_code_fence(response)
        result = json.loads(clean)

        urgency = result.get("urgency", "MEDIUM").lower()
        reason = result.get("reason", "Đánh giá mức độ triệu chứng")
        confidence = float(result.get("confidence", 0.7))

        # Log the triage decision for audit
        safety_audit.log_decision(
            event_type="symptom_triage",
            query=state['query_en'],
            decision=urgency,
            confidence=confidence,
            risk_factors=[reason] if urgency in ["emergency", "high"] else [],
            patient_id=state.get("patient_id"),
            human_review_required=(urgency == "emergency"),
        )

    except CircuitBreakerOpen:
        logger.error("[PatientGraph] LLM circuit breaker open - defaulting to safe escalation")
        urgency = "high"
        reason = "Hệ thống tạm thời không khả dụng, khuyến nghị thăm khám để đảm bảo an toàn"

    except json.JSONDecodeError as e:
        logger.warning(f"[PatientGraph] Triage JSON parse failed: {e}. Using safe default.")
        # When we can't parse, be cautious
        urgency = "medium"
        reason = "Không đọc được kết quả phân loại. Vui lòng mô tả triệu chứng chi tiết hơn"

    except Exception as e:
        logger.warning(f"[PatientGraph] Triage failed: {e}. Defaulting to MEDIUM for safety.")
        urgency = "medium"
        reason = "Đã xảy ra lỗi khi đánh giá mức độ triệu chứng"

    # Safety-first: escalate on emergency or high urgency
    escalation = urgency in ["emergency", "high"]

    return {
        "urgency_level": urgency,
        "escalation_needed": escalation,
        "escalation_reason": reason,
        "current_stage": "triaged",
        "progress": 0.50
    }


async def escalation_handler_node(state: PatientChatState) -> dict:
    """
    Node: Handle urgent cases.
    
    Generates a safe "Go to hospital/doctor" message instead of medical advice.
    """
    logger.info("[PatientGraph] escalation_handler: Generating escalation message...")
    
    reason = state.get("escalation_reason") or "Có dấu hiệu cần được bác sĩ đánh giá ngay."
    msg_en = (
        "Cảnh báo khẩn cấp: Triệu chứng của bạn có thể nghiêm trọng.\n\n"
        "Vui lòng đến cơ sở y tế gần nhất hoặc liên hệ cấp cứu ngay lập tức.\n\n"
        f"Lý do: {reason}"
    )

    if state["urgency_level"] != "emergency":
        msg_en = (
            "Triệu chứng của bạn cần được bác sĩ thăm khám sớm.\n\n"
            "Vui lòng đến bệnh viện/phòng khám trong thời gian sớm nhất và không tự điều trị theo tư vấn AI.\n\n"
            f"Lý do: {reason}"
        )
        
    return {
        "reasoning_en": msg_en,
        "current_stage": "escalated",
        "progress": 0.80
    }


async def patient_reasoning_node(state: PatientChatState) -> dict:
    """
    Node: Generate helpful advice for non-urgent cases.

    Includes defensive responses for uncertainty and hallucination prevention.
    """
    logger.info("[PatientGraph] reasoning: Generating advice...")

    system_prompt = """You are a supportive medical AI assistant for patients.

FORMATTING (very important):
- Greet the patient warmly using their name at the start
- Use **bold** for key medical terms, medication names, or important values
- Break your answer into short paragraphs separated by blank lines
- Use bullet lists (- item) when listing multiple things (e.g. medications, symptoms, advice)
- DO NOT write one continuous block of text
- Keep language simple, warm, and easy to understand
- Respond entirely in Vietnamese

CRITICAL GUIDELINES:
- Be empathetic and clear
- Use simple, non-technical language
- ALWAYS remind them to check with their doctor
- Do NOT prescribe medication or dosages
- Do NOT give definitive diagnoses
- Refuse non-medical requests (poems, stories, entertainment, coding, weather, finance)
- If you are uncertain or don't have enough information, say "Tôi không có đủ thông tin để trả lời chính xác" (I don't have enough information)
- NEVER make up information - only use what's in the patient context

IMPORTANT: If the query is outside your medical knowledge or you're uncertain, respond with:
"Tôi không thể đưa ra lời khuyên cụ thể về vấn đề này. Vui lòng tham khảo ý kiến bác sĩ."
(I cannot provide specific advice on this matter. Please consult a doctor.)"""

    prompt = f"""Patient: {state['patient_profile'].get('full_name')}
Age: {state['patient_profile'].get('age')}
Conditions: {state['patient_profile'].get('chronic_conditions', 'Not specified')}
Medical Context: {state['medical_history']}

Query: {state['query_en']}"""

    try:
        async def _reasoning_call():
            return await llm_client.generate(
                model=settings.medical_model,
                prompt=prompt,
                system=system_prompt,
                stream=False
            )

        response_en = await with_circuit_breaker(
            _llm_breaker,
            retry_async,
            _reasoning_call,
            config=LLM_RETRY_CONFIG,
            operation_name="patient_reasoning"
        )

        # Check for uncertainty in response
        if detect_uncertainty_in_response(response_en, language="vi"):
            logger.info("[PatientGraph] Detected uncertainty in response - adding disclaimer")
            response_en += "\n\n⚠️ Lưu ý: Đây chỉ là thông tin tham khảo chung. Vui lòng trao đổi trực tiếp với bác sĩ để được tư vấn phù hợp."

    except CircuitBreakerOpen:
        logger.error("[PatientGraph] LLM circuit breaker open")
        response_en = create_idk_response(
            reason="Dịch vụ AI y tế đang tạm thời không khả dụng",
            original_query=state['query_en'],
            language="vi",
            suggestions=[
                "Vui lòng thử lại sau vài phút",
                "Nếu khẩn cấp, hãy liên hệ bác sĩ hoặc cơ sở y tế gần nhất",
                "Đến phòng khám hoặc bệnh viện nếu triệu chứng nặng hơn"
            ]
        )

    except Exception as e:
        logger.error(f"[PatientGraph] Reasoning failed: {e}")
        response_en = create_idk_response(
            reason="Đã xảy ra lỗi khi xử lý câu hỏi của bạn",
            original_query=state['query_en'],
            language="vi",
            suggestions=[
                "Vui lòng diễn đạt lại câu hỏi",
                "Mô tả cụ thể hơn về triệu chứng của bạn",
                "Liên hệ bác sĩ nếu triệu chứng kéo dài"
            ]
        )

    # Insert line break after Vietnamese greeting (e.g. "Chào chị Trần Thị Bình,")
    response_en = re.sub(
        r'^(Chào\s+(?:chị|anh|bạn|em|cô|chú|bác)\s+[^,\n]+,)\s*',
        r'\1\n\n',
        response_en,
        count=1,
        flags=re.IGNORECASE
    )

    # Apply paragraph breaks for readability (safety net for dense LLM output)
    response_en = _add_paragraph_breaks(response_en)
    logger.info("[PatientGraph] reasoning: Applied paragraph formatting to response")

    return {
        "reasoning_en": response_en,
        "current_stage": "reasoned",
        "progress": 0.75
    }


async def format_patient_output_node(state: PatientChatState) -> dict:
    """Node: Format output."""
    formatted = format_response(
        response_text=state["reasoning_en"],
        language="vi",
        confidence=0.9 if not state["escalation_needed"] else 1.0
    )
    
    return {
        "formatted_response": formatted,
        "current_stage": "formatted",
        "progress": 0.85
    }


async def translate_patient_output_node(state: PatientChatState) -> dict:
    """Node: Finalize response payload."""
    logger.info("[PatientGraph] translate_output: Finalizing response...")

    response_vi = state["reasoning_en"]

    return {
        "response_vi": response_vi,
        "current_stage": "complete",
        "progress": 1.0
    }


# ============================================================================
# ROUTING
# ============================================================================

def route_triage(state: PatientChatState) -> Literal["escalation_handler", "patient_reasoning"]:
    if state["escalation_needed"]:
        return "escalation_handler"
    return "patient_reasoning"


def route_after_patient_translation(state: PatientChatState) -> Literal["verify_input", "format_output"]:
    """Route after translation; short-circuit out-of-scope requests."""
    if state.get("scope_guard_blocked"):
        return "format_output"
    return "verify_input"


def route_after_patient_verification(state: PatientChatState) -> Literal["get_history", "format_output"]:
    """Route after verification; short-circuit out-of-scope requests."""
    if state.get("scope_guard_blocked"):
        return "format_output"
    return "get_history"


# ============================================================================
# GRAPH BUILDER
# ============================================================================

# Global checkpointer for state persistence
_patient_checkpointer = MemorySaver()


def build_patient_graph():
    """
    Build the patient chat graph with proper checkpointing.

    Returns:
        Compiled StateGraph ready for execution with state persistence
    """
    builder = StateGraph(PatientChatState)

    # Add all nodes
    builder.add_node("translate_input", translate_patient_input_node)
    builder.add_node("verify_input", verify_patient_input_node)
    builder.add_node("get_history", get_patient_history_node)
    builder.add_node("symptom_triage", symptom_triage_node)
    builder.add_node("patient_reasoning", patient_reasoning_node)
    builder.add_node("escalation_handler", escalation_handler_node)
    builder.add_node("format_output", format_patient_output_node)
    builder.add_node("translate_output", translate_patient_output_node)

    # Define edges
    builder.add_edge(START, "translate_input")
    builder.add_conditional_edges(
        "translate_input",
        route_after_patient_translation,
        ["verify_input", "format_output"]
    )
    builder.add_conditional_edges(
        "verify_input",
        route_after_patient_verification,
        ["get_history", "format_output"]
    )
    builder.add_edge("get_history", "symptom_triage")

    # Conditional routing based on triage
    builder.add_conditional_edges(
        "symptom_triage",
        route_triage,
        ["escalation_handler", "patient_reasoning"]
    )

    builder.add_edge("escalation_handler", "format_output")
    builder.add_edge("patient_reasoning", "format_output")
    builder.add_edge("format_output", "translate_output")
    builder.add_edge("translate_output", END)

    # Compile with checkpointer for state persistence (critical for HITL and recovery)
    return builder.compile(checkpointer=_patient_checkpointer)


# ============================================================================
# PUBLIC API
# ============================================================================

_patient_graph = None


def get_patient_graph():
    """Get or create the patient chat graph singleton."""
    global _patient_graph
    if _patient_graph is None:
        _patient_graph = build_patient_graph()
    return _patient_graph


async def process_patient_chat_graph(
    patient_id: str,
    query_vi: str,
    image_path: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    Process patient chat using the LangGraph orchestrator.

    Yields stage updates for real-time UI feedback.

    Args:
        patient_id: ID of the patient
        query_vi: Vietnamese query from patient
        image_path: Optional path to image
        thread_id: Optional thread ID for state persistence

    Yields:
        Stage update dictionaries
    """
    graph = get_patient_graph()
    initial_state = create_initial_patient_state(patient_id, query_vi, image_path)

    # Config for checkpointing - critical for proper state retrieval
    config = {"configurable": {"thread_id": thread_id or f"patient_{patient_id}_{int(__import__('time').time())}"}}

    # Send initial status
    yield create_stage_message("starting", "Đang xử lý câu hỏi của bạn...", 0.05)

    try:
        # Run graph and stream updates
        async for event in graph.astream(initial_state, config=config):
            for node_name, node_output in event.items():
                if node_name == "__interrupt__":
                    # Handle any interrupts (though patient graph typically doesn't use HITL)
                    yield {
                        "stage": "hitl_required",
                        "hitl_request": node_output[0].value if node_output else None
                    }
                    continue

                if isinstance(node_output, dict):
                    stage = node_output.get("current_stage", "processing")
                    progress = node_output.get("progress", 0.0)

                    # Yield progress update with Vietnamese messages
                    stage_messages = {
                        "scope_blocked": "Chỉ hỗ trợ câu hỏi sức khỏe và y tế",
                        "translated_input": "Đã hiểu câu hỏi của bạn",
                        "verified_input": "Đang phân tích nội dung",
                        "retrieved_history": "Đã xem xét hồ sơ y tế",
                        "triaged": "Đang đánh giá mức độ",
                        "escalated": "Đang xử lý tình huống khẩn cấp",
                        "reasoned": "Đang chuẩn bị câu trả lời",
                        "formatted": "Đang định dạng phản hồi",
                        "complete": "Hoàn thành"
                    }

                    yield {
                        "stage": stage,
                        "progress": progress,
                        "message": stage_messages.get(stage, "Đang xử lý...")
                    }

        # CORRECT: Use graph.get_state() to retrieve final accumulated state
        # This is the proper LangGraph pattern instead of capturing last node output
        final_state = graph.get_state(config).values

        if final_state and final_state.get("response_vi"):
            # Add urgency indicator for UI
            urgency_level = final_state.get("urgency_level", "low")
            escalation_needed = final_state.get("escalation_needed", False)

            yield {
                "stage": "complete",
                "message": "Hoàn thành",
                "progress": 1.0,
                "response": final_state["response_vi"],
                "formatted_response": final_state.get("formatted_response"),
                "urgency_level": urgency_level,
                "escalation_needed": escalation_needed,
                "escalation_reason": final_state.get("escalation_reason"),
            }
        else:
            # This shouldn't happen with proper state management
            logger.error("[PatientGraph] Final state missing response_vi")
            yield {
                "stage": "error",
                "message": "Xin lỗi, không thể xử lý câu hỏi của bạn. Vui lòng thử lại.",
                "error": "Failed to generate response"
            }

    except CircuitBreakerOpen as e:
        logger.error(f"[PatientGraph] Circuit breaker open: {e}")
        yield {
            "stage": "error",
            "message": "Hệ thống đang tạm thời quá tải. Vui lòng thử lại sau ít phút hoặc liên hệ bác sĩ trực tiếp nếu cần hỗ trợ khẩn cấp.",
            "error": str(e)
        }

    except Exception as e:
        logger.exception(f"[PatientGraph] Error processing query: {e}")

        # User-friendly Vietnamese error message
        error_message = "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. "
        if "timeout" in str(e).lower():
            error_message += "Hệ thống đang phản hồi chậm. Vui lòng thử lại."
        elif "connection" in str(e).lower():
            error_message += "Không thể kết nối đến dịch vụ. Vui lòng kiểm tra kết nối mạng."
        else:
            error_message += "Vui lòng thử lại hoặc liên hệ hỗ trợ nếu lỗi tiếp tục xảy ra."

        yield {
            "stage": "error",
            "message": error_message,
            "error": str(e)
        }
