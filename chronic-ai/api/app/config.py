from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Resolve .env relative to api/ directory so runtime cwd does not matter.
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        case_sensitive=False,
    )

    # Supabase Configuration - defaults for testing
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    patient_photo_bucket: str = "patient-photos"
    patient_photo_signed_url_ttl_seconds: int = 3600

    # LLM Provider Configuration
    llm_provider: str = "ollama"  # vertex | ollama

    # Vertex AI OpenAI-compatible endpoint configuration
    vertex_ai_host: str = ""
    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    vertex_ai_endpoint_id: str = ""
    vertex_ai_model: str = ""
    vertex_ai_chat_completions_path: str = ""
    vertex_ai_gcloud_command: str = "gcloud"
    vertex_ai_token_ttl_seconds: int = 3300
    vertex_ai_temperature: float = 0.2

    # Legacy Ollama Configuration (optional fallback)
    ollama_host: str = "http://localhost:11434"
    ollama_auto_pull_missing_models: bool = True

    # Application Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # Model Configuration
    medical_model: str = "alibayram/medgemma:4b"
    # Upload pipeline behavior
    # False by default: image uploads go directly to LLM (no OCR in hot path)
    image_upload_run_ocr: bool = False

    # Verification model for input validation + safety checks.
    # In Vertex endpoint mode this typically points to the same deployed endpoint model.
    verification_model: str = "gemma:2b-instruct"
    doctor_reasoning_max_tokens: int = 900
    verification_max_tokens: int = 256

    # Human-in-the-Loop Configuration
    enable_hitl: bool = True
    hitl_confidence_threshold: float = 0.7  # Below this, request clarification
    hitl_safety_threshold: float = 0.8  # Below (1.0 - this), require safety review

    # VinAI Translate Models (HuggingFace) - State-of-the-art Vi-En translation
    # Higher BLEU scores than EnviT5, especially for medical domain
    vinai_vi2en_model: str = "vinai/vinai-translate-vi2en"
    vinai_en2vi_model: str = "vinai/vinai-translate-en2vi"
    # Device options: "auto" (recommended), "mps" (Apple Silicon), "cuda" (NVIDIA), "cpu"
    translation_device: str = "auto"

    # Translation Performance Settings
    translation_cache_enabled: bool = True
    translation_cache_max_size: int = 2000  # LRU cache entries
    translation_cache_ttl: float = 7200.0  # 2 hours TTL
    translation_batch_size: int = 8  # Max texts per batch
    translation_adaptive_beams: bool = True  # Use fewer beams for short texts
    translation_short_text_threshold: int = 50  # tokens - below this use 3 beams

    # Deprecated: EnviT5 settings (kept for backward compatibility)
    envit5_model: str = "VietAI/envit5-translation"  # deprecated
    envit5_device: str = "auto"  # deprecated

    # Embedding settings:
    # - embedding_provider=hash: local deterministic vectors (no external service needed)
    # - embedding_provider=ollama: use Ollama embedding model from embedding_model
    # - embedding_provider=gemini: use Vertex Gemini embedding model from embedding_model
    embedding_model: str = "nomic-embed-text"
    embedding_provider: str = "hash"  # hash | ollama | gemini
    embedding_dimensions: int = 768
    embedding_task_type_document: str = "RETRIEVAL_DOCUMENT"
    embedding_task_type_query: str = "RETRIEVAL_QUERY"

    # Resilience Configuration
    llm_retry_max_attempts: int = 3
    llm_retry_base_delay: float = 1.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 60.0

    # Safety Configuration (Medical AI Best Practices)
    # These thresholds are calibrated for medical use - err on side of caution
    safety_auto_escalate_emergency: bool = True  # Auto-escalate emergency triage
    safety_require_context: bool = True  # Warn when patient context is missing
    safety_max_risk_factors: int = 3  # Above this, require human review

    # Audit Configuration
    enable_safety_audit: bool = True
    audit_retention_entries: int = 10000

    # Deprecated: translation_model no longer used (replaced by envit5_model)
    translation_model: Optional[str] = None

settings = Settings()
