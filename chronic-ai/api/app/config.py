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
from typing import List, Union
import json
from pydantic import AliasChoices, Field, field_validator


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
    llm_provider: str = "ollama"  # vertex | ollama | openai_compatible

    # Vertex AI OpenAI-compatible endpoint configuration
    vertex_ai_host: str = ""
    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    vertex_ai_endpoint_id: str = ""
    vertex_ai_model: str = ""
    vertex_ai_chat_completions_path: str = ""
    # Vertex auth mode:
    # - auto (default): ADC/service-account first, then gcloud fallback
    # - adc: ADC/service-account only
    # - gcloud: gcloud CLI only (local/dev fallback)
    vertex_ai_auth_method: str = "auto"
    # Optional inline service account JSON (plain or base64) for environments
    # where mounting credential files is not convenient (e.g. Render).
    vertex_ai_service_account_json: str = ""
    vertex_ai_service_account_json_base64: str = ""
    vertex_ai_gcloud_command: str = "gcloud"
    vertex_ai_token_ttl_seconds: int = 3300
    vertex_ai_token_scopes: str = "https://www.googleapis.com/auth/cloud-platform"
    vertex_ai_temperature: float = 0.2

    # OpenAI-compatible endpoint configuration (for providers like Featherless)
    openai_compatible_base_url: str = ""
    openai_compatible_chat_completions_path: str = "/chat/completions"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    openai_compatible_temperature: float = 0.2
    # Request timeout controls for OpenAI-compatible providers.
    # Some gateways time out around 60s; keep total timeout close to that.
    openai_compatible_timeout_seconds: float = 70.0
    openai_compatible_connect_timeout_seconds: float = 15.0
    # If a long response fails (timeout/5xx), retry once with smaller max_tokens.
    openai_compatible_fallback_max_tokens: int = 700

    # Legacy Ollama Configuration (optional fallback)
    ollama_host: str = "http://localhost:11434"
    ollama_auto_pull_missing_models: bool = True

    # Hugging Face access (for MedSigLIP model download, if gated/rate-limited)
    hf_token: str = ""

    # Application Configuration
    fastapi_host: str = "0.0.0.0"
    # Render injects PORT, while local dev usually uses FASTAPI_PORT.
    fastapi_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("FASTAPI_PORT", "PORT"),
    )
    cors_origins: Union[str, List[str]] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> List[str]:
        """Accept a JSON array string or a plain comma-separated string, and strip trailing slashes."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                origins = json.loads(v)
                if isinstance(origins, str):
                    origins = [origins]
            except json.JSONDecodeError:
                # Treat as comma-separated list
                origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            origins = v
        else:
            return []

        # Ensure all origins are strings and strip trailing slashes
        return [str(o).rstrip("/") for o in origins if o]

    # Model Configuration
    medical_model: str = "alibayram/medgemma"
    # Optional dedicated model for upload-file AI analysis (especially image uploads).
    # If empty, upload analysis falls back to medical_model.
    upload_analysis_model: str = ""
    # ECG Classifier Remote Endpoint
    ecg_classifier_endpoint_url: str = ""  # Any HTTP endpoint that accepts {"image_base64": "..."}
    ecg_classifier_endpoint_timeout: int = 60
    # Auth type: none | bearer | api_key | vertex_gcloud (default, backward-compat)
    ecg_classifier_auth_type: str = "vertex_gcloud"
    ecg_classifier_bearer_token: str = ""   # Used when auth_type=bearer
    ecg_classifier_api_key: str = ""        # Used when auth_type=api_key
    ecg_classifier_api_key_header: str = "X-API-Key"  # Header name for api_key auth
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
    # - embedding_provider=gemini: use Gemini embeddings API key route
    #   (falls back to Vertex Gemini route when GEMINI_API_KEY is not set)
    # - embedding_provider=ollama: use Ollama embedding model from embedding_model
    # - embedding_provider=hash: local deterministic vectors (no external service needed)
    embedding_model: str = "gemini-embedding-001"
    embedding_provider: str = "gemini"  # gemini | ollama | hash
    embedding_dimensions: int = 768
    embedding_task_type_document: str = "RETRIEVAL_DOCUMENT"
    embedding_task_type_query: str = "RETRIEVAL_QUERY"
    gemini_api_key: str = ""
    gemini_embedding_api_base: str = "https://generativelanguage.googleapis.com"
    gemini_embedding_api_version: str = "v1beta"

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
