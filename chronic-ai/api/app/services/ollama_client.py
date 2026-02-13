"""
Ollama Client Wrapper with Memory Management.

Provides async interface to Ollama for:
- Text generation (translation, medical reasoning)
- Embedding generation
- Model loading/unloading for memory optimization
"""
import asyncio
import httpx
import logging
from typing import AsyncGenerator, Optional, List, Union
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for Ollama API with memory management."""
    
    def __init__(self, host: str = None):
        self.host = host or settings.ollama_host
        self.timeout = httpx.Timeout(300.0, connect=60.0)
        self._loaded_model: Optional[str] = None
        self._model_locks: dict[str, asyncio.Lock] = {}
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        stream: bool = False,
        num_predict: int = 2048
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate text using specified model.
        
        Args:
            model: Model name (e.g., 'alibayram/medgemma:4b')
            prompt: User prompt
            system: Optional system prompt
            images: Optional list of base64-encoded images for multimodal models
            stream: Whether to stream the response
            num_predict: Maximum number of tokens to generate (default: 2048)
            
        Returns:
            Full response text if stream=False, else async generator of tokens
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": num_predict
            }
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
                try:
                    return await self._request_embedding(client, text, model)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404 and self._is_model_missing_error(e.response, model):
                        if not settings.ollama_auto_pull_missing_models:
                            raise RuntimeError(
                                f"Ollama embedding model '{model}' is not installed. "
                                f"Run: ollama pull {model}"
                            )

                        logger.warning(
                            "Embedding model '%s' is missing. Attempting to pull it from Ollama registry.",
                            model,
                        )
                        ensured = await self.ensure_model_available(model)
                        if not ensured:
                            raise RuntimeError(
                                f"Ollama embedding model '{model}' is not available after pull attempt. "
                                f"Run: ollama pull {model}"
                            )

                        return await self._request_embedding(client, text, model)
                    raise
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama embedding request timed out for model '{model}'")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 and self._is_model_missing_error(e.response, model):
                raise RuntimeError(
                    f"Ollama embedding model '{model}' is not installed. "
                    f"Run: ollama pull {model}"
                )
            raise RuntimeError(
                f"Ollama embedding error ({e.response.status_code}): "
                f"{e.response.text[:200] if e.response.text else 'No response'}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    async def _request_embedding(
        self,
        client: httpx.AsyncClient,
        text: str,
        model: str
    ) -> List[float]:
        """
        Request embeddings with Ollama endpoint compatibility.

        Tries /api/embeddings first, then falls back to /api/embed if needed.
        """
        response = await client.post(
            f"{self.host}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            }
        )

        if response.status_code == 404 and not self._is_model_missing_error(response, model):
            # Newer Ollama versions expose /api/embed instead of /api/embeddings.
            response = await client.post(
                f"{self.host}/api/embed",
                json={
                    "model": model,
                    "input": text
                }
            )

        response.raise_for_status()
        return self._extract_embedding(response.json())

    @staticmethod
    def _extract_embedding(payload: dict) -> List[float]:
        """Normalize embedding payload shape across Ollama API variants."""
        embedding = payload.get("embedding")
        if isinstance(embedding, list) and embedding:
            return embedding

        embeddings = payload.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            # /api/embed may return [[...]] for single input, or [...] in some variants.
            first = embeddings[0]
            if isinstance(first, list):
                return first
            if isinstance(first, (int, float)):
                return embeddings

        raise RuntimeError("Ollama embedding response is missing embedding vector")

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract Ollama error message from JSON or fallback text."""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                value = payload.get("error")
                if value:
                    return str(value)
        except Exception:
            pass
        return response.text or ""

    def _is_model_missing_error(self, response: httpx.Response, model: str) -> bool:
        """Detect Ollama's model-not-found error shape."""
        message = self._extract_error_message(response).lower()
        if response.status_code != 404 or "not found" not in message or "model" not in message:
            return False
        model_lower = model.lower()
        return model_lower in message or f"\"{model_lower}\"" in message

    
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
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama registry.

        Returns:
            True if the model is available after pull, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/pull",
                    json={
                        "model": model,
                        "stream": False,
                    },
                )
                response.raise_for_status()
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama pull timed out for model '{model}'")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama pull error ({e.response.status_code}): "
                f"{e.response.text[:200] if e.response.text else 'No response'}"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama pull failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

        return await self.check_model_available(model)

    async def ensure_model_available(self, model: str) -> bool:
        """Ensure a model is available locally, pulling it if needed."""
        if await self.check_model_available(model):
            return True

        lock = self._model_locks.setdefault(model, asyncio.Lock())
        async with lock:
            if await self.check_model_available(model):
                return True
            return await self.pull_model(model)

    async def check_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        return any(
            name == model or name.startswith(f"{model}:")
            for name in model_names
        )
    
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
