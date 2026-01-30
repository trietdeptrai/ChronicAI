"""Services module.

Contains core business logic for ChronicAI:
- ollama_client: Async Ollama API wrapper
- rag: RAG pipeline (chunking, embeddings, search)
- llm: Translation Sandwich pipeline
- ocr: PaddleOCR integration
"""
from app.services.ollama_client import ollama_client, OllamaClient
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

__all__ = [
    # Ollama Client
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
    "OCRService"
]
