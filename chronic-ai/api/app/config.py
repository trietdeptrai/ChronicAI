from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Supabase Configuration - defaults for testing
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    
    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    
    # Application Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Model Configuration
    medical_model: str = "thiagomoraes/medgemma-1.5-4b-it:Q8_0"
    
    # EnviT5 Translation Model (HuggingFace)
    envit5_model: str = "VietAI/envit5-translation"
    envit5_device: str = "cuda"  # or "cpu" if no GPU available
    
    embedding_model: str = "nomic-embed-text"
    
    # Deprecated: translation_model no longer used (replaced by envit5_model)
    translation_model: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
