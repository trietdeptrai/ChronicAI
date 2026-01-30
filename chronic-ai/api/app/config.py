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
    medical_model: str = "alibayram/medgemma:4b"
    translation_model: str = "qwen2.5:1.5b"
    embedding_model: str = "nomic-embed-text"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
