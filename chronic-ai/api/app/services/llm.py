"""
Translation Sandwich Pipeline (LLM Service).

Implements the three-step translation process:
1. Vietnamese → English (Qwen 2.5)
2. Medical Reasoning (MedGemma 4B) with RAG context
3. English → Vietnamese (Qwen 2.5)

Includes memory optimization through model unloading.
"""
from typing import AsyncGenerator, Optional
from uuid import UUID
import base64
from pathlib import Path

from app.services.ollama_client import ollama_client
from app.services.rag import get_patient_context
from app.config import settings


# System prompts for translation
VI_TO_EN_SYSTEM = """You are a professional medical translator. 
Translate the following Vietnamese text to English accurately.
Preserve all medical terminology and context.
Output ONLY the English translation, nothing else."""

EN_TO_VI_SYSTEM = """You are a professional medical translator.
Translate the following English text to Vietnamese.
Use appropriate Vietnamese medical terminology.
The translation should be natural and easy to understand for Vietnamese patients.
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

Remember: You are a support tool, not a replacement for professional medical advice."""


async def translate_vi_to_en(text: str) -> str:
    """
    Translate Vietnamese to English using Qwen 2.5.
    
    Args:
        text: Vietnamese text to translate
        
    Returns:
        English translation
    """
    response = await ollama_client.generate(
        model=settings.translation_model,
        prompt=text,
        system=VI_TO_EN_SYSTEM,
        stream=False
    )
    return response


async def translate_en_to_vi(text: str) -> str:
    """
    Translate English to Vietnamese using Qwen 2.5.
    
    Args:
        text: English text to translate
        
    Returns:
        Vietnamese translation
    """
    response = await ollama_client.generate(
        model=settings.translation_model,
        prompt=text,
        system=EN_TO_VI_SYSTEM,
        stream=False
    )
    return response


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
        A. Vietnamese → English (Qwen 2.5)
        B. Medical Reasoning (MedGemma 4B) + RAG Context
        C. English → Vietnamese (Qwen 2.5)
    
    Yields:
        Dict with stage info and content for real-time UI updates
        
    Args:
        user_input_vi: User's question in Vietnamese
        patient_id: Patient UUID for context retrieval
        image_path: Optional path to medical image
    """
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
    
    query_en = await translate_vi_to_en(user_input_vi)
    
    yield {
        "stage": "translating_input",
        "message": "Hoàn thành dịch sang tiếng Anh",
        "progress": 0.25,
        "translation": query_en
    }
    
    # ========== Memory Optimization: Unload translator ==========
    await ollama_client.unload(settings.translation_model)
    
    # ========== STEP B: Medical Reasoning with RAG ==========
    yield {
        "stage": "retrieving_context",
        "message": "Đang tìm kiếm hồ sơ y tế liên quan...",
        "progress": 0.35
    }
    
    # Get patient context via RAG
    patient_context = await get_patient_context(
        patient_id=patient_id,
        query=query_en,
        max_chunks=10
    )
    
    yield {
        "stage": "medical_reasoning",
        "message": "Đang phân tích y khoa...",
        "progress": 0.5
    }
    
    # Medical reasoning with MedGemma
    response_en = await medical_reasoning(
        query_en=query_en,
        patient_context=patient_context,
        image_base64=image_base64
    )
    
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
    
    response_vi = await translate_en_to_vi(response_en)
    
    yield {
        "stage": "complete",
        "message": "Hoàn thành",
        "progress": 1.0,
        "response": response_vi,
        "response_en": response_en  # Include English for doctor reference
    }


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
    
    await ollama_client.unload(settings.translation_model)
    
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
        "translation_model": await ollama_client.check_model_available(
            settings.translation_model
        ),
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
