"""
Doctor Orchestrator Service (DEPRECATED).

⚠️ DEPRECATION WARNING ⚠️
This module is deprecated and will be removed in a future version.

Please use the new LangGraph-based orchestration instead:
- app.services.doctor_graph.process_doctor_query_graph() for doctor queries
- app.services.patient_graph.process_patient_chat_graph() for patient chat

The new implementation provides:
- Human-in-the-loop (HITL) support for clarifications and approvals
- Retry logic with circuit breakers for reliability
- Fuzzy patient name matching for better accuracy
- Response caching for performance
- Safety audit logging
- Better Vietnamese error messages

Migration Guide:
    # Old (deprecated):
    from app.services.orchestrator import process_doctor_query
    async for update in process_doctor_query(query_vi):
        ...

    # New (recommended):
    from app.services.doctor_graph import process_doctor_query_graph
    async for update in process_doctor_query_graph(query_vi):
        ...

Handles doctor queries that can reference any patient without pre-selection.
Extracts patient mentions from queries and aggregates multi-patient context.
"""
import warnings
from typing import AsyncGenerator, List, Optional
from uuid import UUID
from dataclasses import dataclass
import json
import logging
import time

from app.services.llm_client import llm_client
from app.services.json_utils import strip_markdown_code_fence
from app.services.rag import get_patient_context, get_patient_record_image_attachments
from app.services.llm import (
    translate_vi_to_en,
    translate_en_to_vi,
    MEDICAL_REASONING_SYSTEM
)
from app.db.database import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)

# Emit deprecation warning when module is imported
warnings.warn(
    "app.services.orchestrator is deprecated. "
    "Use app.services.doctor_graph.process_doctor_query_graph() instead.",
    DeprecationWarning,
    stacklevel=2
)


@dataclass
class PatientMatch:
    """Represents a matched patient from the database."""
    id: str
    name: str
    primary_diagnosis: Optional[str]
    match_confidence: float


# System prompt for patient name extraction
PATIENT_EXTRACTION_SYSTEM = """You are a medical assistant that extracts patient names from doctor queries.
Given a query in English, identify any patient names mentioned.

Output ONLY a JSON array of patient names. If no patients are mentioned, output an empty array [].
Do not include any other text or explanation.

Examples:
- Query: "What is the status of patient Tran Thi Binh?" -> ["Tran Thi Binh"]
- Query: "Compare the glucose levels of Nguyen Van A and Le Thi B" -> ["Nguyen Van A", "Le Thi B"]
- Query: "Which patients need urgent attention?" -> []
- Query: "How is Binh doing today?" -> ["Binh"]
"""

# System prompt for doctor orchestrator reasoning
DOCTOR_REASONING_SYSTEM = """You are a medical AI assistant helping doctors manage multiple patients.
You have access to patient records and can answer questions about specific patients or aggregate across patients.
You are assisting: {doctor_name}

IMPORTANT GUIDELINES:
- Address the user as "{doctor_name}" or "Bác sĩ" (Doctor).
- When asked about specific patients, provide detailed analysis based on their records
- When asked aggregate questions (e.g., "which patients need attention"), analyze all relevant data
- Always identify patients by name in your responses
- Flag urgent cases that require immediate attention
- Provide evidence-based recommendations
- Be concise but thorough

CRITICAL - HANDLING MISSING DATA:
- NEVER output placeholder text like [Insert...], [TODO], [N/A], [Date unknown], etc.
- NEVER output placeholders for names like [Doctor Name], [Dr. Name], etc.
- If specific data is not available in the provided context, state it naturally in your response
- Example: Instead of "[Insert Last Checkup Date]", say "I don't have the last checkup date for this patient on record"
- Only answer based on information actually present in the patient context
- If important data is missing, suggest the doctor add it to the patient record

Remember: You are supporting a doctor's decision-making, not replacing their clinical judgment."""


async def extract_patient_mentions(query_en: str) -> List[str]:
    """
    Use LLM to extract patient names from doctor's query.
    
    Args:
        query_en: Doctor's query in English
        
    Returns:
        List of patient names mentioned in the query
    """
    response = await llm_client.generate(
        model=settings.medical_model,  # Use MedGemma for structured extraction
        prompt=f"Query: {query_en}",
        system=PATIENT_EXTRACTION_SYSTEM,
        stream=False
    )
    
    # Parse JSON response
    try:
        # Clean up response (remove markdown code blocks if present)
        clean_response = strip_markdown_code_fence(response)
        
        names = json.loads(clean_response)
        return names if isinstance(names, list) else []
    except json.JSONDecodeError:
        # Fallback: return empty if parsing fails
        return []


async def resolve_patients(names: List[str]) -> List[PatientMatch]:
    """
    Search database for patients matching mentioned names.
    
    Args:
        names: List of patient names to search for
        
    Returns:
        List of matched patients with confidence scores
    """
    if not names:
        return []
    
    supabase = get_supabase()
    matches = []
    
    for name in names:
        # Search by name (case-insensitive partial match)
        result = supabase.table("patients").select(
            "id, full_name, primary_diagnosis"
        ).ilike(
            "full_name", f"%{name}%"
        ).limit(5).execute()
        
        if result.data:
            for patient in result.data:
                # Calculate simple match confidence
                full_name = patient.get("full_name", "").lower()
                search_name = name.lower()
                
                if full_name == search_name:
                    confidence = 1.0
                elif search_name in full_name:
                    confidence = 0.9
                else:
                    confidence = 0.7
                
                matches.append(PatientMatch(
                    id=patient["id"],
                    name=patient["full_name"],
                    primary_diagnosis=patient.get("primary_diagnosis"),
                    match_confidence=confidence
                ))
    
    # Deduplicate by ID, keeping highest confidence
    unique_matches = {}
    for match in matches:
        if match.id not in unique_matches or match.match_confidence > unique_matches[match.id].match_confidence:
            unique_matches[match.id] = match
    
    return list(unique_matches.values())


async def get_multi_patient_context(
    patient_ids: List[UUID],
    query: str
) -> str:
    """
    Aggregate context from multiple patients for the query.
    
    Args:
        patient_ids: List of patient UUIDs
        query: The doctor's query for context relevance
        
    Returns:
        Combined context string from all patients
    """
    if not patient_ids:
        return "No specific patients identified. Please mention patient names to get detailed information."
    
    context_parts = []
    
    for patient_id in patient_ids:
        patient_context = await get_patient_context(
            patient_id=patient_id,
            query=query,
            max_chunks=5  # Fewer chunks per patient when multiple
        )
        context_parts.append(patient_context)
        context_parts.append("\n---\n")  # Separator between patients
    
    return "\n".join(context_parts)


async def get_aggregate_patient_overview() -> str:
    """
    Get overview of all patients for aggregate queries.
    
    Returns:
        Summary of all patients with priority/status info
    """
    supabase = get_supabase()
    
    # Get patients summary
    result = supabase.table("patients").select(
        "id, full_name, primary_diagnosis, triage_priority, "
        "profile_status, last_checkup_date"
    ).eq("profile_status", "active").order(
        "triage_priority", desc=True  # Urgent first
    ).limit(50).execute()
    
    if not result.data:
        return "No active patients found."
    
    overview_parts = ["## Active Patients Overview\n"]
    
    # Group by priority
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


async def process_doctor_query(
    query_vi: str,
    image_path: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Full doctor orchestrator pipeline with streaming.

    ⚠️ DEPRECATED: Use process_doctor_query_graph() from doctor_graph module instead.

    Steps:
        1. Vietnamese → English translation
        2. Extract patient mentions from query
        3. Resolve patients from database
        4. Get multi-patient or aggregate context
        5. Medical reasoning with MedGemma
        6. English → Vietnamese translation

    Yields:
        Dict with stage info and content for real-time UI updates

    Args:
        query_vi: Doctor's question in Vietnamese
        image_path: Optional path to an image file to analyze
    """
    warnings.warn(
        "process_doctor_query() is deprecated. "
        "Use process_doctor_query_graph() from app.services.doctor_graph instead.",
        DeprecationWarning,
        stacklevel=2
    )
    import base64
    from pathlib import Path
    
    # Load image if provided
    image_base64 = None
    if image_path:
        path = Path(image_path)
        if path.exists():
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
    start_total = time.perf_counter()
    # ========== STEP 1: Vietnamese → English ==========
    yield {
        "stage": "translating_input",
        "message": "Đang dịch câu hỏi...",
        "progress": 0.1
    }
    
    logger.info(f"[Orchestrator] Step 1: Input query (Vi): {query_vi}")
    start_step_1 = time.perf_counter()
    query_en = await translate_vi_to_en(query_vi)
    elapsed_1 = (time.perf_counter() - start_step_1) * 1000
    logger.info(f"[Orchestrator] Step 1: Took {elapsed_1:.1f} ms")
    logger.info(f"[Orchestrator] Step 1: Translated query (En): {query_en}")
    
    yield {
        "stage": "translating_input",
        "message": "Hoàn thành dịch sang tiếng Anh",
        "progress": 0.15,
        "translation": query_en
    }
    
    # ========== STEP 2: Extract Patient Mentions ==========
    yield {
        "stage": "extracting_patients",
        "message": "Đang xác định bệnh nhân được nhắc đến...",
        "progress": 0.2
    }
    
    start_step_2 = time.perf_counter()
    mentioned_names = await extract_patient_mentions(query_en)
    elapsed_2 = (time.perf_counter() - start_step_2) * 1000
    logger.info(f"[Orchestrator] Step 2: Took {elapsed_2:.1f} ms")
    
    # ========== STEP 3: Resolve Patients ==========
    yield {
        "stage": "resolving_patients",
        "message": "Đang tìm kiếm hồ sơ bệnh nhân...",
        "progress": 0.3
    }
    
    start_step_3 = time.perf_counter()
    matched_patients = await resolve_patients(mentioned_names)
    elapsed_3 = (time.perf_counter() - start_step_3) * 1000
    logger.info(f"[Orchestrator] Step 3: Took {elapsed_3:.1f} ms")
    patient_ids = [UUID(p.id) for p in matched_patients]
    
    # Format patient info for response
    mentioned_patients = [
        {
            "id": p.id,
            "name": p.name,
            "match_confidence": p.match_confidence
        }
        for p in matched_patients
    ]
    
    yield {
        "stage": "resolving_patients",
        "message": f"Tìm thấy {len(matched_patients)} bệnh nhân",
        "progress": 0.35,
        "mentioned_patients": mentioned_patients
    }
    
    # Unload medical model to free memory
    await llm_client.unload(settings.medical_model)
    
    # ========== STEP 4: Get Context ==========
    yield {
        "stage": "retrieving_context",
        "message": "Đang tổng hợp thông tin y tế...",
        "progress": 0.4
    }
    
    start_step_4 = time.perf_counter()
    if patient_ids:
        # Get context for specific patients
        patient_context = await get_multi_patient_context(patient_ids, query_vi)
    else:
        # Get aggregate overview for general queries
        patient_context = await get_aggregate_patient_overview()
    elapsed_4 = (time.perf_counter() - start_step_4) * 1000
    logger.info(f"[Orchestrator] Step 4: Took {elapsed_4:.1f} ms")
    
    yield {
        "stage": "retrieving_context",
        "message": "Hoàn thành tổng hợp thông tin",
        "progress": 0.5
    }
    
    # ========== STEP 5: Medical Reasoning ==========
    yield {
        "stage": "medical_reasoning",
        "message": "Đang phân tích y khoa...",
        "progress": 0.6
    }
    
    reasoning_prompt = f"""## Patient Context
{patient_context}

## Doctor's Query
{query_en}

Please provide a helpful, accurate response to assist the doctor with patient management."""

    # Default to demo doctor for now since we don't have auth context
    doctor_name = "BS. Nguyễn Văn An"
    
    # Format system prompt with doctor name
    system_prompt = DOCTOR_REASONING_SYSTEM.format(doctor_name=doctor_name)

    logger.info(f"[Orchestrator] Step 5: MedGemma prompt length: {len(reasoning_prompt)} chars")
    logger.debug(f"[Orchestrator] Step 5: MedGemma prompt: {reasoning_prompt[:500]}...")
    
    start_step_5 = time.perf_counter()
    response_en = await llm_client.generate(
        model=settings.medical_model,
        prompt=reasoning_prompt,
        system=system_prompt,
        images=[image_base64] if image_base64 else None,
        stream=False
    )
    elapsed_5 = (time.perf_counter() - start_step_5) * 1000
    logger.info(f"[Orchestrator] Step 5: Took {elapsed_5:.1f} ms")
    
    logger.info(f"[Orchestrator] Step 5: MedGemma response (En): {response_en[:300]}..." if len(response_en) > 300 else f"[Orchestrator] Step 5: MedGemma response (En): {response_en}")
    
    yield {
        "stage": "medical_reasoning",
        "message": "Hoàn thành phân tích",
        "progress": 0.75,
        "response_en": response_en
    }
    
    # Unload medical model
    await llm_client.unload(settings.medical_model)
    
    # ========== STEP 6: English → Vietnamese ==========
    yield {
        "stage": "translating_output",
        "message": "Đang dịch phản hồi sang tiếng Việt...",
        "progress": 0.85
    }
    
    logger.info(f"[Orchestrator] Step 6: Translating MedGemma response to Vietnamese")
    start_step_6 = time.perf_counter()
    response_vi = await translate_en_to_vi(response_en)
    elapsed_6 = (time.perf_counter() - start_step_6) * 1000
    logger.info(f"[Orchestrator] Step 6: Took {elapsed_6:.1f} ms")
    logger.info(f"[Orchestrator] Step 6: Final response (Vi): {response_vi[:300]}..." if len(response_vi) > 300 else f"[Orchestrator] Step 6: Final response (Vi): {response_vi}")

    attachments = []
    if matched_patients:
        for patient in matched_patients:
            patient_attachments = await get_patient_record_image_attachments(
                patient_id=UUID(patient.id),
                patient_name=patient.name,
                limit=2
            )
            if patient_attachments:
                attachments.extend(patient_attachments)
        attachments = attachments[:6]
    
    yield {
        "stage": "complete",
        "message": "Hoàn thành",
        "progress": 1.0,
        "response": response_vi,
        "response_en": response_en,
        "mentioned_patients": mentioned_patients,
        "attachments": attachments
    }
    elapsed_total = (time.perf_counter() - start_total) * 1000
    logger.info(f"[Orchestrator] Pipeline total: Took {elapsed_total:.1f} ms")
