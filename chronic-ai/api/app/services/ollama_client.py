"""
Ollama Client Wrapper with Memory Management.

Provides async interface to Ollama for:
- Text generation (translation, medical reasoning)
- Embedding generation
- Model loading/unloading for memory optimization
"""
import httpx
from typing import AsyncGenerator, Optional, List, Union
from app.config import settings


class OllamaClient:
    """Async client for Ollama API with memory management."""
    
    def __init__(self, host: str = None):
        self.host = host or settings.ollama_host
        self.timeout = httpx.Timeout(120.0, connect=30.0)
        self._loaded_model: Optional[str] = None
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate text using specified model.
        
        Args:
            model: Model name (e.g., 'qwen2.5:1.5b', 'alibayram/medgemma:4b')
            prompt: User prompt
            system: Optional system prompt
            images: Optional list of base64-encoded images for multimodal models
            stream: Whether to stream the response
            
        Returns:
            Full response text if stream=False, else async generator of tokens
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
            
        if images:
            payload["images"] = images
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return self._stream_response(client, payload)
                else:
                    response = await client.post(
                        f"{self.host}/api/generate",
                        json=payload
                    )
                    response.raise_for_status()
                    return response.json()["response"]
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama request timed out for model '{model}'")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama error ({e.response.status_code}): {e.response.text[:200] if e.response.text else 'No response'}")
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    
    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens."""
        async with client.stream(
            "POST",
            f"{self.host}/api/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    async def embed(self, text: str, model: str = None) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Embedding model (defaults to nomic-embed-text)
            
        Returns:
            768-dimensional embedding vector
        """
        model = model or settings.embedding_model
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                return response.json()["embedding"]
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama embedding request timed out for model '{model}'")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama embedding error ({e.response.status_code}): {e.response.text[:200] if e.response.text else 'No response'}")
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    
    async def embed_batch(
        self,
        texts: List[str],
        model: str = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model
            
        Returns:
            List of 768-dimensional embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text, model)
            embeddings.append(embedding)
        return embeddings
    
    async def unload(self, model: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model: Model name to unload
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Setting keep_alive to 0 unloads the model
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": model,
                        "keep_alive": 0
                    }
                )
                response.raise_for_status()
                self._loaded_model = None
                return True
        except Exception:
            # Unload failures are non-critical, just return False
            return False

    
    async def list_models(self) -> List[dict]:
        """List available models."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
    
    async def check_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        return any(model in name for name in model_names)
    
    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
ollama_client = OllamaClient()
