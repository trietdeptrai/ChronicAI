"""
RAG (Retrieval-Augmented Generation) Pipeline.

Provides document ingestion, embedding storage, and similarity search
for patient medical records using pgvector.
"""
from typing import List, Optional
from uuid import UUID
import json

from app.services.ollama_client import ollama_client
from app.db.database import get_supabase


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: Source text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of overlapping characters between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for boundary in ['. ', '.\n', '! ', '? ', '\n\n']:
                last_boundary = text[start:end].rfind(boundary)
                if last_boundary > chunk_size * 0.5:  # At least 50% of chunk
                    end = start + last_boundary + len(boundary)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


async def generate_embedding(text: str) -> List[float]:
    """
    Generate 768-dimensional embedding for text using nomic-embed-text.
    
    Args:
        text: Text to embed
        
    Returns:
        768-dimensional embedding vector
    """
    return await ollama_client.embed(text)


async def ingest_document(
    text: str,
    record_id: UUID,
    chunk_size: int = 500,
    overlap: int = 50
) -> int:
    """
    Chunk text, generate embeddings, and store in pgvector.
    
    Args:
        text: Document text content
        record_id: UUID of the associated medical record
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        Number of chunks stored
    """
    supabase = get_supabase()
    
    # Split into chunks
    chunks = chunk_text(text, chunk_size, overlap)
    
    # Generate and store embeddings
    for idx, chunk in enumerate(chunks):
        embedding = await generate_embedding(chunk)
        
        # Insert into record_embeddings table
        supabase.table("record_embeddings").insert({
            "record_id": str(record_id),
            "chunk_content": chunk,
            "embedding": embedding,
            "chunk_index": idx
        }).execute()
    
    return len(chunks)


async def ingest_image(
    image_text: str,
    record_id: UUID
) -> int:
    """
    Ingest OCR-extracted text from image into RAG system.
    
    Args:
        image_text: Text extracted from image via OCR
        record_id: UUID of the associated medical record
        
    Returns:
        Number of chunks stored
    """
    # Use smaller chunks for OCR text (often fragmented)
    return await ingest_document(
        text=image_text,
        record_id=record_id,
        chunk_size=300,
        overlap=30
    )


async def search_similar_records(
    query: str,
    patient_id: UUID,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> List[dict]:
    """
    Search for similar medical records using cosine similarity.
    
    Args:
        query: Search query text
        patient_id: Patient UUID to filter records
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score
        
    Returns:
        List of matching records with similarity scores
    """
    supabase = get_supabase()
    
    # Generate query embedding
    query_embedding = await generate_embedding(query)
    
    # Perform vector similarity search via Supabase RPC
    # Note: This requires a custom function in Supabase
    result = supabase.rpc(
        "search_patient_records",
        {
            "query_embedding": query_embedding,
            "patient_uuid": str(patient_id),
            "match_count": top_k,
            "match_threshold": similarity_threshold
        }
    ).execute()
    
    return result.data if result.data else []


async def get_patient_context(
    patient_id: UUID,
    query: Optional[str] = None,
    max_chunks: int = 10
) -> str:
    """
    Aggregate relevant medical context for a patient.
    
    Args:
        patient_id: Patient UUID
        query: Optional query to filter relevant context
        max_chunks: Maximum number of chunks to include
        
    Returns:
        Formatted context string for LLM consumption
    """
    supabase = get_supabase()
    
    context_parts = []
    
    # 1. Get basic patient info (handle non-existent patients gracefully)
    try:
        patient_result = supabase.table("patients").select(
            "full_name, date_of_birth, gender, chronic_conditions, "
            "current_medications, allergies, primary_diagnosis"
        ).eq("id", str(patient_id)).maybe_single().execute()
    except Exception:
        patient_result = None
    
    if patient_result and patient_result.data:
        patient = patient_result.data
        context_parts.append(f"""
## Thông tin bệnh nhân (Patient Information)
- **Họ tên**: {patient.get('full_name', 'N/A')}
- **Ngày sinh**: {patient.get('date_of_birth', 'N/A')}
- **Giới tính**: {patient.get('gender', 'N/A')}
- **Chẩn đoán chính**: {patient.get('primary_diagnosis', 'N/A')}
- **Bệnh mãn tính**: {json.dumps(patient.get('chronic_conditions', []), ensure_ascii=False)}
- **Thuốc đang dùng**: {json.dumps(patient.get('current_medications', []), ensure_ascii=False)}
- **Dị ứng**: {', '.join(patient.get('allergies', []))}
""")
    
    # 2. Get recent vital signs
    vitals_result = supabase.table("vital_signs").select(
        "recorded_at, blood_pressure_systolic, blood_pressure_diastolic, "
        "heart_rate, blood_glucose, blood_glucose_timing, oxygen_saturation"
    ).eq("patient_id", str(patient_id)).order(
        "recorded_at", desc=True
    ).limit(5).execute()
    
    if vitals_result.data:
        context_parts.append("\n## Sinh hiệu gần đây (Recent Vitals)")
        for vital in vitals_result.data:
            bp = f"{vital.get('blood_pressure_systolic', 'N/A')}/{vital.get('blood_pressure_diastolic', 'N/A')}"
            context_parts.append(
                f"- {vital.get('recorded_at', 'N/A')}: "
                f"HA: {bp} mmHg, "
                f"Nhịp tim: {vital.get('heart_rate', 'N/A')} bpm, "
                f"SpO2: {vital.get('oxygen_saturation', 'N/A')}%"
            )
    
    # 3. Get relevant medical records via similarity search
    if query:
        similar_records = await search_similar_records(
            query=query,
            patient_id=patient_id,
            top_k=max_chunks
        )
        
        if similar_records:
            context_parts.append("\n## Hồ sơ y tế liên quan (Relevant Medical Records)")
            for record in similar_records:
                context_parts.append(f"- {record.get('chunk_content', '')}")
    else:
        # Get recent records without query
        records_result = supabase.table("medical_records").select(
            "record_type, title, content_text, created_at"
        ).eq("patient_id", str(patient_id)).order(
            "created_at", desc=True
        ).limit(5).execute()
        
        if records_result.data:
            context_parts.append("\n## Hồ sơ y tế gần đây (Recent Medical Records)")
            for record in records_result.data:
                context_parts.append(
                    f"- [{record.get('record_type', 'N/A')}] "
                    f"{record.get('title', 'N/A')}: "
                    f"{record.get('content_text', '')[:200]}..."
                )
    
    return "\n".join(context_parts)


async def delete_record_embeddings(record_id: UUID) -> bool:
    """
    Delete all embeddings for a medical record.
    
    Args:
        record_id: Medical record UUID
        
    Returns:
        True if successful
    """
    supabase = get_supabase()
    supabase.table("record_embeddings").delete().eq(
        "record_id", str(record_id)
    ).execute()
    return True
