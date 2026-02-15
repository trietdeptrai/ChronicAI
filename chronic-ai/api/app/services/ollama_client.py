"""Legacy compatibility shim for old import paths.

Prefer importing from `app.services.llm_client`.
"""

from app.services.llm_client import LLMClient, llm_client, OllamaClient, ollama_client

__all__ = ["LLMClient", "llm_client", "OllamaClient", "ollama_client"]
