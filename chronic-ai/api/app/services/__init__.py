"""Services module.

Contains core business logic for ChronicAI:
- llm_client: Provider-routed LLM API wrapper (Vertex/Ollama)
- rag: RAG pipeline (chunking, embeddings, search)
- llm: Translation Sandwich pipeline
- ocr: PaddleOCR integration
- doctor_graph: LangGraph-based doctor orchestration
- patient_graph: LangGraph-based patient chat orchestration
- verification_service: Input verification with Gemma 2B
- output_formatter: Structured response formatting
- resilience: Retry logic, circuit breakers, and defensive responses (NEW)
"""
from app.services.llm_client import llm_client, LLMClient, ollama_client, OllamaClient
from app.services.rag import (
    chunk_text,
    generate_embedding,
    ingest_document,
    ingest_image,
    search_similar_records,
    get_patient_context,
    delete_record_embeddings
)
from app.services.llm import (
    translate_vi_to_en,
    translate_en_to_vi,
    medical_reasoning,
    process_medical_query,
    generate_clinical_summary,
    check_system_health
)
from app.services.ocr import (
    get_ocr_service,
    extract_text,
    OCRService
)

# LangGraph-based orchestration (NEW)
from app.services.doctor_graph import (
    get_doctor_graph,
    process_doctor_query_graph,
    build_doctor_graph
)
from app.services.patient_graph import (
    get_patient_graph,
    process_patient_chat_graph,
    build_patient_graph
)
from app.services.verification_service import (
    verify_input,
    check_response_safety,
    should_request_clarification,
    should_require_safety_review,
    get_safety_level
)
from app.services.resilience import (
    retry_async,
    with_retry,
    RetryConfig,
    CircuitBreaker,
    get_circuit_breaker,
    with_circuit_breaker,
    CircuitBreakerOpen,
    create_idk_response,
    create_defensive_response,
    safety_audit,
    SafetyAuditLogger
)
from app.services.cache import (
    response_cache,
    ResponseCache,
    get_cached_response,
    cache_response,
    invalidate_patient_cache
)
from app.services.output_formatter import (
    format_response,
    format_as_html,
    format_as_markdown,
    format_as_plain_text
)
from app.services.graph_state import (
    DoctorOrchestratorState,
    PatientChatState,
    QueryType,
    FormattedResponse,
    create_initial_doctor_state
)

__all__ = [
    # LLM Client (preferred names)
    "llm_client",
    "LLMClient",
    # Legacy aliases
    "ollama_client",
    "OllamaClient",
    # RAG Pipeline
    "chunk_text",
    "generate_embedding",
    "ingest_document",
    "ingest_image",
    "search_similar_records",
    "get_patient_context",
    "delete_record_embeddings",
    # LLM Pipeline
    "translate_vi_to_en",
    "translate_en_to_vi",
    "medical_reasoning",
    "process_medical_query",
    "generate_clinical_summary",
    "check_system_health",
    # OCR
    "get_ocr_service",
    "extract_text",
    "OCRService",
    # LangGraph Orchestration
    "get_doctor_graph",
    "process_doctor_query_graph",
    "build_doctor_graph",
    "get_patient_graph",
    "process_patient_chat_graph",
    "build_patient_graph",
    # Verification
    "verify_input",
    "check_response_safety",
    "should_request_clarification",
    "should_require_safety_review",
    "get_safety_level",
    # Output Formatting
    "format_response",
    "format_as_html",
    "format_as_markdown",
    "format_as_plain_text",
    # State Schemas
    "DoctorOrchestratorState",
    "PatientChatState",
    "QueryType",
    "FormattedResponse",
    "create_initial_doctor_state",
    # Resilience
    "retry_async",
    "with_retry",
    "RetryConfig",
    "CircuitBreaker",
    "get_circuit_breaker",
    "with_circuit_breaker",
    "CircuitBreakerOpen",
    "create_idk_response",
    "create_defensive_response",
    "safety_audit",
    "SafetyAuditLogger",
    # Caching
    "response_cache",
    "ResponseCache",
    "get_cached_response",
    "cache_response",
    "invalidate_patient_cache",
]
