"""
LangGraph State Schemas for ChronicAI Orchestration.

Defines TypedDict states for the doctor and patient orchestration graphs,
including support for human-in-the-loop (HITL) interrupts.
"""
from typing import TypedDict, Annotated, Optional, List, Literal, Any
from operator import add
from dataclasses import dataclass
from enum import Enum


class QueryType(str, Enum):
    """Types of doctor queries for routing."""
    PATIENT_SPECIFIC = "patient_specific"  # About specific patient(s)
    AGGREGATE = "aggregate"  # Overview of all patients
    GENERAL = "general"  # General medical question
    IMAGE_ANALYSIS = "image_analysis"  # Image-based query


class ResponseSection(TypedDict):
    """A section of the formatted response."""
    type: str  # "assessment", "analysis", "recommendations", "warnings"
    icon: str
    title: str
    content: Optional[str]
    items: Optional[List[str]]  # For list-type sections


class FormattedResponse(TypedDict):
    """Structured response format for better UI display."""
    sections: List[ResponseSection]
    confidence: float
    sources: List[str]
    raw_text: str  # Original unformatted text


class PatientMatch(TypedDict):
    """A patient match from database lookup."""
    id: str
    name: str
    primary_diagnosis: Optional[str]
    match_confidence: float


class HITLRequest(TypedDict):
    """Human-in-the-loop interrupt request."""
    type: Literal[
        "clarification_needed",
        "approval_required",
        "patient_confirmation",
        "safety_review"
    ]
    message: str
    details: dict
    options: Optional[List[str]]  # For multiple choice


class VerificationResult(TypedDict):
    """Result from input verification."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggested_rewrites: List[str]
    needs_clarification: bool


# ============================================================================
# DOCTOR ORCHESTRATOR STATE
# ============================================================================

class DoctorOrchestratorState(TypedDict):
    """
    State for the doctor orchestration graph.
    
    This state flows through all nodes and accumulates information
    as the query is processed through translation, verification,
    patient lookup, medical reasoning, and output formatting.
    """
    # === Input Stage ===
    query_vi: str  # Original Vietnamese query
    query_en: str  # Translated English query
    image_path: Optional[str]  # Path to uploaded image (if any)
    image_base64: Optional[str]  # Base64 encoded image (user-uploaded)
    enable_hitl: bool  # Per-request HITL toggle (also controls fast-path checks)

    # === Patient Record Images ===
    patient_record_images_base64: List[str]  # Base64 encoded patient record images from DB
    
    # === Verification Stage ===
    verification_result: Optional[VerificationResult]
    input_confidence: float
    human_approved_input: Optional[bool]  # None = not required, True/False = decision
    
    # === Patient Routing Stage ===
    mentioned_patient_names: List[str]  # Names extracted from query
    matched_patients: List[PatientMatch]  # Resolved from database
    patient_context: str  # Aggregated context from RAG
    query_type: QueryType
    record_attachments: List[dict]  # Signed image attachments for UI
    
    # === Medical Reasoning Stage ===
    reasoning_en: str  # Raw English response from MedGemma
    safety_score: float  # 0-1 risk assessment
    safety_issues: List[str]  # Identified risk factors
    human_approved_output: Optional[bool]  # None = not required
    
    # === Output Stage ===
    response_vi: str  # Final Vietnamese response
    formatted_response: Optional[FormattedResponse]
    
    # === Progress Tracking ===
    current_stage: str
    progress: float  # 0.0 to 1.0
    stage_messages: Annotated[List[dict], add]  # Accumulate stage updates
    
    # === Error Handling ===
    errors: Annotated[List[str], add]
    
    # === HITL State ===
    hitl_request: Optional[HITLRequest]
    hitl_response: Optional[Any]  # Response from human


# ============================================================================
# PATIENT CHAT STATE
# ============================================================================

class PatientChatState(TypedDict):
    """
    State for patient-facing chat graph.
    
    Simpler than doctor state, focused on single patient context
    with safety-first approach and escalation triggers.
    """
    # === Input ===
    patient_id: str
    query_vi: str
    query_en: str
    image_path: Optional[str]
    
    # === Patient Context ===
    patient_profile: dict
    medical_history: str
    
    # === Processing ===
    verification_result: Optional[VerificationResult]
    reasoning_en: str
    
    # === Safety ===
    urgency_level: Literal["low", "medium", "high", "emergency"]
    escalation_needed: bool
    escalation_reason: Optional[str]
    
    # === Output ===
    response_vi: str
    formatted_response: Optional[FormattedResponse]
    
    # === Meta ===
    current_stage: str
    progress: float
    errors: Annotated[List[str], add]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_initial_doctor_state(
    query_vi: str,
    image_path: Optional[str] = None,
    enable_hitl: bool = True,
) -> DoctorOrchestratorState:
    """Create initial state for doctor orchestrator graph."""
    return DoctorOrchestratorState(
        # Input
        query_vi=query_vi,
        query_en="",
        image_path=image_path,
        image_base64=None,
        enable_hitl=enable_hitl,

        # Patient record images
        patient_record_images_base64=[],

        # Verification
        verification_result=None,
        input_confidence=1.0,
        human_approved_input=None,
        
        # Patient routing
        mentioned_patient_names=[],
        matched_patients=[],
        patient_context="",
        query_type=QueryType.GENERAL,
        
        # Reasoning
        reasoning_en="",
        safety_score=1.0,
        safety_issues=[],
        human_approved_output=None,
        
        # Output
        response_vi="",
        formatted_response=None,
        
        # Progress
        current_stage="initialized",
        progress=0.0,
        stage_messages=[],
        
        # Errors
        errors=[],
        
        # HITL
        hitl_request=None,
        hitl_response=None,

        # Attachments
        record_attachments=[]
    )


def create_stage_message(
    stage: str,
    message: str,
    progress: float,
    **kwargs
) -> dict:
    """Create a stage update message for streaming to UI."""
    return {
        "stage": stage,
        "message": message,
        "progress": progress,
        **kwargs
    }
