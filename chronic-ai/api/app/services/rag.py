"""
RAG (Retrieval-Augmented Generation) Pipeline.

Provides document ingestion, embedding storage, and similarity search
for patient medical records using pgvector.
"""
import base64
import logging
from typing import List, Optional, Tuple
from uuid import UUID
import json

from app.services.llm_client import llm_client
from app.db.database import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)


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


async def generate_embedding(text: str, *, for_query: bool = False) -> List[float]:
    """
    Generate embedding for text using configured embedding provider.
    
    Args:
        text: Text to embed
        for_query: Whether the text is a search query (vs document chunk)
        
    Returns:
        Embedding vector
    """
    task_type = (
        settings.embedding_task_type_query
        if for_query
        else settings.embedding_task_type_document
    )
    return await llm_client.embed(text, task_type=task_type)


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
        embedding = await generate_embedding(chunk, for_query=False)
        
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
    query_embedding = await generate_embedding(query, for_query=True)
    
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
- **Dị ứng**: {', '.join(patient.get('allergies') or [])}
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
            top_k=max_chunks,
            similarity_threshold=0.7
        )

        # Fallback: lower threshold if nothing matched
        if not similar_records:
            similar_records = await search_similar_records(
                query=query,
                patient_id=patient_id,
                top_k=max_chunks,
                similarity_threshold=0.5
            )

        if similar_records:
            context_parts.append("\n## Hồ sơ y tế liên quan (Relevant Medical Records)")
            for record in similar_records:
                context_parts.append(f"- {record.get('chunk_content', '')}")
        else:
            # Fallback to recent records if vector search yields nothing
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


def _extract_signed_url(signed: object) -> Optional[str]:
    if isinstance(signed, dict):
        return (
            signed.get("signedURL")
            or signed.get("signed_url")
            or (signed.get("data") or {}).get("signedURL")
            or (signed.get("data") or {}).get("signed_url")
        )
    return None


async def get_patient_record_image_attachments(
    patient_id: UUID,
    patient_name: Optional[str] = None,
    limit: int = 3
) -> List[dict]:
    """
    Fetch signed URLs for recent medical record images for a patient.

    Returns attachment objects suitable for chat UI rendering.
    """
    supabase = get_supabase()

    try:
        result = supabase.table("medical_records").select(
            "id, record_type, title, image_path, created_at"
        ).eq("patient_id", str(patient_id)).order(
            "created_at", desc=True
        ).limit(limit * 3).execute()
    except Exception:
        return []

    attachments: List[dict] = []
    for record in result.data or []:
        image_path = record.get("image_path")
        if not image_path:
            continue

        try:
            signed = supabase.storage.from_(settings.patient_photo_bucket).create_signed_url(
                image_path,
                settings.patient_photo_signed_url_ttl_seconds
            )
        except Exception:
            continue
        signed_url = _extract_signed_url(signed)
        if not signed_url:
            continue

        attachments.append({
            "type": "image",
            "url": signed_url,
            "record_id": record.get("id"),
            "record_type": record.get("record_type"),
            "title": record.get("title"),
            "created_at": record.get("created_at"),
            "patient_id": str(patient_id),
            "patient_name": patient_name,
        })

        if len(attachments) >= limit:
            break

    return attachments


async def get_patient_record_images_base64(
    patient_id: UUID,
    limit: int = 3
) -> Tuple[List[str], List[dict]]:
    """
    Fetch and base64 encode patient medical record images from storage.

    This function downloads actual image content for LLM analysis,
    unlike get_patient_record_image_attachments which only returns URLs.

    Args:
        patient_id: Patient UUID
        limit: Maximum number of images to return

    Returns:
        Tuple of (list of base64 encoded images, list of attachment metadata)
    """
    supabase = get_supabase()

    try:
        result = supabase.table("medical_records").select(
            "id, record_type, title, image_path, created_at"
        ).eq("patient_id", str(patient_id)).not_.is_(
            "image_path", "null"
        ).order(
            "created_at", desc=True
        ).limit(limit * 2).execute()
    except Exception as e:
        logger.warning(f"Failed to fetch patient records: {e}")
        return [], []

    images_base64: List[str] = []
    attachments: List[dict] = []

    for record in result.data or []:
        image_path = record.get("image_path")
        if not image_path:
            continue

        try:
            # Download actual image bytes from Supabase storage
            image_bytes = supabase.storage.from_(
                settings.patient_photo_bucket
            ).download(image_path)

            if image_bytes:
                # Encode to base64
                encoded = base64.b64encode(image_bytes).decode("utf-8")
                images_base64.append(encoded)

                # Create signed URL for UI display
                signed = supabase.storage.from_(
                    settings.patient_photo_bucket
                ).create_signed_url(
                    image_path,
                    settings.patient_photo_signed_url_ttl_seconds
                )
                signed_url = _extract_signed_url(signed)

                attachments.append({
                    "type": "image",
                    "url": signed_url,
                    "record_id": record.get("id"),
                    "record_type": record.get("record_type"),
                    "title": record.get("title"),
                    "created_at": record.get("created_at"),
                    "patient_id": str(patient_id),
                })

                logger.info(
                    f"Loaded image for analysis: {record.get('title')} "
                    f"({len(image_bytes)} bytes)"
                )

        except Exception as e:
            logger.warning(f"Failed to download image {image_path}: {e}")
            continue

        if len(images_base64) >= limit:
            break

    logger.info(
        f"Loaded {len(images_base64)} patient record images for LLM analysis"
    )
    return images_base64, attachments
