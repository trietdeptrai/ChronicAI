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
from typing import AsyncGenerator, Literal, Optional
from uuid import UUID

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
from app.services.ollama_client import ollama_client
from app.services.transformers_client import transformers_client
from app.services.rag import get_patient_context
from app.services.verification_service import (
    verify_input,
    check_response_safety,
    should_require_safety_review
)
from app.services.output_formatter import format_response, get_urgency_indicator
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
_ollama_breaker = get_circuit_breaker("ollama_patient", failure_threshold=3, recovery_timeout=60.0)
_db_breaker = get_circuit_breaker("database_patient", failure_threshold=5, recovery_timeout=30.0)

# Retry configuration for LLM calls
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    retryable_exceptions=(RuntimeError, TimeoutError, ConnectionError)
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
    """Node: Translate Vietnamese input to English."""
    logger.info(f"[PatientGraph] translate_input: {state['query_vi'][:50]}...")
    
    query_en = await transformers_client.translate_vi_to_en(state["query_vi"])
    
    return {
        "query_en": query_en,
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
    
    return {
        "verification_result": verification,
        "current_stage": "verified_input",
        "progress": 0.25
    }


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
1. EMERGENCY: Life-threatening (chest pain, stroke signs, heavy bleeding, difficulty breathing, loss of consciousness) -> requires immediate hospital
2. HIGH: Severe symptoms needing doctor visit in 24h (high fever, severe pain, significant bleeding)
3. MEDIUM: Bothersome symptoms needing appointment (persistent symptoms, moderate discomfort)
4. LOW: General questions or mild symptoms (health inquiries, mild symptoms)

IMPORTANT: When in doubt, err on the side of caution and classify higher.

Output ONLY valid JSON: {"urgency": "level", "reason": "brief reason", "confidence": 0.0-1.0}"""

    triage_prompt = f"""Patient Profile: {state['patient_profile'].get('age')}yo {state['patient_profile'].get('gender')}
Conditions: {state['patient_profile'].get('chronic_conditions')}
Query: {state['query_en']}"""

    urgency = "medium"  # Safe default
    reason = "Unable to assess"
    confidence = 0.5

    try:
        # Use circuit breaker and retry logic
        async def _triage_call():
            return await ollama_client.generate(
                model=settings.medical_model,
                prompt=triage_prompt,
                system=triage_system,
                stream=False,
                num_predict=128
            )

        response = await with_circuit_breaker(
            _ollama_breaker,
            retry_async,
            _triage_call,
            config=LLM_RETRY_CONFIG,
            operation_name="symptom_triage"
        )

        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(clean)

        urgency = result.get("urgency", "MEDIUM").lower()
        reason = result.get("reason", "Triage assessment")
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
        logger.error("[PatientGraph] Ollama circuit breaker open - defaulting to safe escalation")
        urgency = "high"
        reason = "System unavailable - recommending medical consultation as precaution"

    except json.JSONDecodeError as e:
        logger.warning(f"[PatientGraph] Triage JSON parse failed: {e}. Using safe default.")
        # When we can't parse, be cautious
        urgency = "medium"
        reason = "Unable to parse triage response - please describe symptoms in more detail"

    except Exception as e:
        logger.warning(f"[PatientGraph] Triage failed: {e}. Defaulting to MEDIUM for safety.")
        urgency = "medium"
        reason = "Triage analysis encountered an error"

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
    
    msg_en = f"Based on your symptoms ({state['escalation_reason']}), please go to a hospital or see a doctor immediately. Do not rely on AI for this."
    
    if state["urgency_level"] == "emergency":
        msg_en = f"EMERGENCY WARNING: These symptoms suggest a serious condition. Please call emergency services or go to the nearest hospital immediately.\n\nReason: {state['escalation_reason']}"
        
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

CRITICAL GUIDELINES:
- Be empathetic and clear
- Use simple, non-technical language
- ALWAYS remind them to check with their doctor
- Do NOT prescribe medication or dosages
- Do NOT give definitive diagnoses
- If you are uncertain or don't have enough information, say "Tôi không có đủ thông tin để trả lời chính xác" (I don't have enough information)
- NEVER make up information - only use what's in the patient context

Format response with:
1. Understanding (empathic acknowledgment)
2. Explanation (simple terms, based ONLY on provided context)
3. Self-care suggestions (safe home remedies only)
4. When to see a doctor (always include this)

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
            return await ollama_client.generate(
                model=settings.medical_model,
                prompt=prompt,
                system=system_prompt,
                stream=False
            )

        response_en = await with_circuit_breaker(
            _ollama_breaker,
            retry_async,
            _reasoning_call,
            config=LLM_RETRY_CONFIG,
            operation_name="patient_reasoning"
        )

        # Check for uncertainty in response
        if detect_uncertainty_in_response(response_en, language="en"):
            logger.info("[PatientGraph] Detected uncertainty in response - adding disclaimer")
            response_en += "\n\n⚠️ Please note: This information is general guidance only. Always consult your healthcare provider for personalized medical advice."

    except CircuitBreakerOpen:
        logger.error("[PatientGraph] Ollama circuit breaker open")
        response_en = create_idk_response(
            reason="The medical AI service is temporarily unavailable",
            original_query=state['query_en'],
            language="en",
            suggestions=[
                "Please try again in a few minutes",
                "Contact your healthcare provider directly if urgent",
                "Visit a local clinic or hospital for immediate concerns"
            ]
        )

    except Exception as e:
        logger.error(f"[PatientGraph] Reasoning failed: {e}")
        response_en = create_idk_response(
            reason=f"An error occurred while processing your question",
            original_query=state['query_en'],
            language="en",
            suggestions=[
                "Please rephrase your question",
                "Provide more specific details about your symptoms",
                "Contact your healthcare provider if symptoms persist"
            ]
        )

    return {
        "reasoning_en": response_en,
        "current_stage": "reasoned",
        "progress": 0.75
    }


async def format_patient_output_node(state: PatientChatState) -> dict:
    """Node: Format output."""
    formatted = format_response(
        response_text=state["reasoning_en"],
        language="en",
        confidence=0.9 if not state["escalation_needed"] else 1.0
    )
    
    return {
        "formatted_response": formatted,
        "current_stage": "formatted",
        "progress": 0.85
    }


async def translate_patient_output_node(state: PatientChatState) -> dict:
    """Node: Translate to Vi."""
    logger.info("[PatientGraph] translate_output: Translating...")
    
    response_vi = await transformers_client.translate_en_to_vi(state["reasoning_en"])
    
    # Translate structured content if needed
    if state.get("formatted_response"):
        formatted = state["formatted_response"].copy()
        for section in formatted["sections"]:
            if section.get("content"):
                section["content"] = await transformers_client.translate_en_to_vi(section["content"])
            if section.get("items"):
                section["items"] = [
                    await transformers_client.translate_en_to_vi(item) 
                    for item in section["items"]
                ]
    
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
    builder.add_edge("translate_input", "verify_input")
    builder.add_edge("verify_input", "get_history")
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
