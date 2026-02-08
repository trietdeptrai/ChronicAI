from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Supabase Configuration - defaults for testing
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    patient_photo_bucket: str = "patient-photos"
    patient_photo_signed_url_ttl_seconds: int = 3600

    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"

    # Application Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # Model Configuration
    medical_model: str = "thiagomoraes/medgemma-1.5-4b-it:Q8_0"

    # Verification Model (Gemma 2B instruct for input validation + safety checks)
    verification_model: str = "gemma:2b-instruct"

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

    embedding_model: str = "nomic-embed-text"

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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
