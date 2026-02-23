from pathlib import Path
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError as e:  # pragma: no cover
    raise ModuleNotFoundError(
        "Missing dependency 'pydantic-settings'.\n\n"
        "This usually happens when `uvicorn` is being run from a different Python "
        "environment than the one you installed dependencies into.\n\n"
        "Fix (from `chronic-ai/api`):\n"
        "  python3 -m pip install -r requirements.txt\n"
        "  python3 -m uvicorn app.main:app --reload\n"
    ) from e
from typing import List


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

    # Hugging Face access (for MedSigLIP model download, if gated/rate-limited)
    hf_token: str = ""

    # Application Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # Model Configuration
    medical_model: str = "alibayram/medgemma"
    # ECG Classifier Vertex AI Endpoint
    ecg_classifier_endpoint_url: str = ""  # e.g. https://<endpoint>.prediction.vertexai.goog/predict
    ecg_classifier_endpoint_timeout: int = 60
    # Upload pipeline behavior
    # False by default: image uploads go directly to LLM (no OCR in hot path)
    image_upload_run_ocr: bool = False
    # Import OCR controls (PDF patient import)
    import_pdf_ocr_dpi: int = 140
    import_pdf_ocr_max_pages: int = 25
    # Metadata preview only needs early profile pages in the export PDF.
    import_metadata_pdf_ocr_max_pages: int = 3
    import_pdf_ocr_preprocess: bool = False
    import_pdf_render_threads: int = 2

    # Verification model for input validation + safety checks.
    # In Vertex endpoint mode this typically points to the same deployed endpoint model.
    verification_model: str = "alibayram/medgemma"
    doctor_reasoning_max_tokens: int = 1400
    verification_max_tokens: int = 256

    # Human-in-the-Loop Configuration
    enable_hitl: bool = True
    hitl_confidence_threshold: float = 0.7  # Below this, request clarification
    hitl_safety_threshold: float = 0.8  # Below (1.0 - this), require safety review

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

settings = Settings()
