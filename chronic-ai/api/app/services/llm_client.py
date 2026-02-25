"""
LLM client wrapper.

Supports:
- Vertex AI OpenAI-compatible chat completions (default)
- OpenAI-compatible chat completions (e.g. Featherless)
- Legacy Ollama generation fallback
- Embeddings via local hash vectors (default), Ollama, Gemini API, or Vertex Gemini
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import AsyncGenerator, List, Optional, Union

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_COMPATIBLE_PROVIDER_ALIASES = {"openai_compatible", "openai", "featherless"}


def is_openai_compatible_provider(provider: Optional[str] = None) -> bool:
    """Return True when provider should use the OpenAI-compatible route."""
    selected = (provider or settings.llm_provider or "vertex").strip().lower()
    return selected in OPENAI_COMPATIBLE_PROVIDER_ALIASES


class LLMClient:
    """
    Backward-compatible client interface used across the codebase.

    Despite the class name, this client routes generation by configured provider.
    """

    def __init__(self, host: str = None):
        # Legacy Ollama host is retained for optional embedding/provider fallback.
        self.host = host or settings.ollama_host
        self.timeout = httpx.Timeout(300.0, connect=60.0)
        self._loaded_model: Optional[str] = None
        self._model_locks: dict[str, asyncio.Lock] = {}

        self._provider = (settings.llm_provider or "vertex").strip().lower()
        self._embedding_provider = (settings.embedding_provider or "hash").strip().lower()

        # Access token cache for Vertex auth.
        self._token_lock = asyncio.Lock()
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        stream: bool = False,
        num_predict: int = 2048,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate text using configured provider.

        Args:
            model: Model name
            prompt: User prompt
            system: Optional system prompt
            images: Optional base64 image list
            stream: Stream output if True
            num_predict: Max generated tokens
        """
        if self._provider == "ollama":
            return await self._generate_ollama(
                model=model,
                prompt=prompt,
                system=system,
                images=images,
                stream=stream,
                num_predict=num_predict,
            )

        if is_openai_compatible_provider(self._provider):
            if stream:
                return self._stream_openai_compatible_response(
                    model=model,
                    prompt=prompt,
                    system=system,
                    images=images,
                    num_predict=num_predict,
                )
            return await self._generate_openai_compatible(
                model=model,
                prompt=prompt,
                system=system,
                images=images,
                num_predict=num_predict,
            )

        # Vertex provider (default).
        if stream:
            return self._stream_vertex_response(
                model=model,
                prompt=prompt,
                system=system,
                images=images,
                num_predict=num_predict,
            )

        return await self._generate_vertex(
            model=model,
            prompt=prompt,
            system=system,
            images=images,
            num_predict=num_predict,
        )

    async def _generate_openai_compatible(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        num_predict: int = 2048,
    ) -> str:
        url = self._openai_compatible_chat_completions_url()
        headers = self._openai_compatible_headers()
        token_candidates = self._openai_compatible_token_candidates(num_predict)
        fallback_mode = len(token_candidates) > 1

        try:
            async with httpx.AsyncClient(timeout=self._openai_compatible_timeout()) as client:
                for idx, max_tokens in enumerate(token_candidates):
                    try:
                        payload = self._build_openai_compatible_payload(
                            model=model,
                            prompt=prompt,
                            system=system,
                            images=images,
                            num_predict=max_tokens,
                            stream=False,
                            include_system_role=True,
                        )
                        response = await client.post(
                            url,
                            headers=headers,
                            json=payload,
                        )
                        if response.status_code >= 400:
                            error_text = self._extract_http_error(response)
                            if response.status_code == 400 and self._is_role_alternation_error(error_text):
                                logger.warning(
                                    "OpenAI-compatible endpoint rejected system role ordering; retrying without system role"
                                )
                                fallback_payload = self._build_openai_compatible_payload(
                                    model=model,
                                    prompt=prompt,
                                    system=system,
                                    images=images,
                                    num_predict=max_tokens,
                                    stream=False,
                                    include_system_role=False,
                                )
                                response = await client.post(
                                    url,
                                    headers=headers,
                                    json=fallback_payload,
                                )
                            response.raise_for_status()
                        return self._extract_vertex_text(response.json())
                    except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
                        if fallback_mode and idx + 1 < len(token_candidates):
                            logger.warning(
                                "OpenAI-compatible call failed with %s at max_tokens=%d; retrying with max_tokens=%d",
                                type(e).__name__,
                                max_tokens,
                                token_candidates[idx + 1],
                            )
                            continue
                        if isinstance(e, httpx.TimeoutException):
                            raise RuntimeError("OpenAI-compatible request timed out")
                        raise RuntimeError(
                            f"OpenAI-compatible generation failed: {type(e).__name__}: {str(e) or 'Unknown error'}"
                        )
                    except httpx.HTTPStatusError as e:
                        status_code = e.response.status_code
                        if (
                            fallback_mode
                            and idx + 1 < len(token_candidates)
                            and self._is_retryable_openai_status(status_code)
                        ):
                            logger.warning(
                                "OpenAI-compatible call returned %d at max_tokens=%d; retrying with max_tokens=%d",
                                status_code,
                                max_tokens,
                                token_candidates[idx + 1],
                            )
                            continue
                        raise RuntimeError(
                            f"OpenAI-compatible error ({status_code}): "
                            f"{self._extract_http_error(e.response)}"
                        )
                raise RuntimeError("OpenAI-compatible generation failed before response parsing")
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to OpenAI-compatible endpoint at {self._host_from_url(url)}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"OpenAI-compatible generation failed: {type(e).__name__}: {str(e) or 'Unknown error'}"
            )

    async def _generate_ollama(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        stream: bool = False,
        num_predict: int = 2048,
    ) -> Union[str, AsyncGenerator[str, None]]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": num_predict,
            },
        }

        if system:
            payload["system"] = system

        if images:
            payload["images"] = images

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return self._stream_response(client, payload)
                response = await client.post(
                    f"{self.host}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()["response"]
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama request timed out for model '{model}'")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama error ({e.response.status_code}): "
                f"{e.response.text[:300] if e.response.text else 'No response'}"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    async def _generate_vertex(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        num_predict: int = 2048,
    ) -> str:
        payload = self._build_vertex_payload(
            model=model,
            prompt=prompt,
            system=system,
            images=images,
            num_predict=num_predict,
            stream=False,
        )
        headers = await self._vertex_headers()
        primary_url = self._vertex_chat_completions_url()
        candidate_urls = [primary_url]
        custom_path = (settings.vertex_ai_chat_completions_path or "").strip()
        fallback_host = self._default_vertex_service_host()
        configured_host = self._normalize_vertex_host(settings.vertex_ai_host or "")
        # Dedicated endpoint hosts (prediction.vertexai.goog) must NOT be routed
        # through the shared aiplatform.googleapis.com domain.
        is_dedicated_host = "prediction.vertexai.goog" in configured_host.lower()
        if (
            configured_host
            and configured_host != fallback_host
            and not custom_path
            and not is_dedicated_host
        ):
            candidate_urls.append(self._vertex_chat_completions_url(host_override=fallback_host))

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                last_connect_error: Optional[Exception] = None
                for idx, url in enumerate(candidate_urls):
                    try:
                        response = await client.post(
                            url,
                            headers=headers,
                            json=payload,
                        )
                        response.raise_for_status()
                        return self._extract_vertex_text(response.json())
                    except httpx.ConnectError as e:
                        last_connect_error = e
                        if idx + 1 < len(candidate_urls):
                            logger.warning(
                                "Vertex host '%s' unreachable, retrying with fallback host '%s'",
                                configured_host or self._default_vertex_service_host(),
                                fallback_host,
                            )
                            continue
                        raise
                if last_connect_error:
                    raise last_connect_error
                raise RuntimeError("Vertex generation failed before request dispatch")
        except httpx.ConnectError:
            tried_hosts = [self._host_from_url(url) for url in candidate_urls]
            raise RuntimeError(
                "Cannot connect to Vertex AI endpoint host(s): "
                + ", ".join(tried_hosts)
            )
        except httpx.TimeoutException:
            raise RuntimeError("Vertex AI request timed out")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Vertex AI error ({e.response.status_code}): "
                f"{self._extract_http_error(e.response)}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Vertex generation failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: dict,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from Ollama."""
        async with client.stream(
            "POST",
            f"{self.host}/api/generate",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]

    async def _stream_vertex_response(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        images: Optional[List[str]],
        num_predict: int,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming compatibility for existing call sites.

        Current implementation emits one final chunk. This preserves the interface
        used by the rest of the codebase without introducing SSE complexity.
        """
        text = await self._generate_vertex(
            model=model,
            prompt=prompt,
            system=system,
            images=images,
            num_predict=num_predict,
        )
        if text:
            yield text

    async def _stream_openai_compatible_response(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        images: Optional[List[str]],
        num_predict: int,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming compatibility for existing call sites.

        Current implementation emits one final chunk. This preserves the interface
        used by the rest of the codebase without introducing SSE complexity.
        """
        text = await self._generate_openai_compatible(
            model=model,
            prompt=prompt,
            system=system,
            images=images,
            num_predict=num_predict,
        )
        if text:
            yield text

    def _default_vertex_service_host(self) -> str:
        location = (settings.vertex_ai_location or "us-central1").strip() or "us-central1"
        return f"https://{location}-aiplatform.googleapis.com"

    @staticmethod
    def _host_from_url(url: str) -> str:
        if not url:
            return ""
        parts = url.split("/", 3)
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}"
        return url

    @staticmethod
    def _normalize_vertex_host(raw_host: str) -> str:
        """
        Normalize configured Vertex host.

        Accepts values with or without scheme. If scheme is missing, defaults to https.
        """
        host = (raw_host or "").strip().rstrip("/")
        if not host:
            return ""
        if re.match(r"^https?://", host, flags=re.IGNORECASE):
            return host
        return f"https://{host}"

    def _vertex_chat_completions_url(self, host_override: Optional[str] = None) -> str:
        host = self._normalize_vertex_host(host_override or settings.vertex_ai_host or "")
        if not host:
            host = self._default_vertex_service_host()

        custom_path = (settings.vertex_ai_chat_completions_path or "").strip()
        if custom_path:
            if not custom_path.startswith("/"):
                custom_path = f"/{custom_path}"
            return f"{host}{custom_path}"

        project = (settings.vertex_ai_project_id or "").strip()
        location = (settings.vertex_ai_location or "").strip()
        endpoint_id = (settings.vertex_ai_endpoint_id or "").strip()

        if not project or not location or not endpoint_id:
            raise RuntimeError(
                "Vertex AI route requires VERTEX_AI_PROJECT_ID, VERTEX_AI_LOCATION, and VERTEX_AI_ENDPOINT_ID"
            )

        return (
            f"{host}/v1/projects/{project}/locations/{location}/endpoints/{endpoint_id}/chat/completions"
        )

    def _openai_compatible_chat_completions_url(self) -> str:
        raw_base = (settings.openai_compatible_base_url or "").strip()
        if not raw_base:
            raise RuntimeError(
                "OpenAI-compatible route requires OPENAI_COMPATIBLE_BASE_URL"
            )
        base = self._normalize_vertex_host(raw_base)
        path = (settings.openai_compatible_chat_completions_path or "").strip() or "/chat/completions"
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    @staticmethod
    def _is_retryable_openai_status(status_code: int) -> bool:
        return status_code in {408, 409, 425, 429, 500, 502, 503, 504}

    @staticmethod
    def _openai_compatible_timeout() -> httpx.Timeout:
        total = max(float(settings.openai_compatible_timeout_seconds), 5.0)
        connect = max(float(settings.openai_compatible_connect_timeout_seconds), 1.0)
        connect = min(connect, total)
        return httpx.Timeout(total, connect=connect)

    @staticmethod
    def _openai_compatible_token_candidates(num_predict: int) -> List[int]:
        primary_tokens = max(int(num_predict), 128)
        fallback_tokens = max(int(settings.openai_compatible_fallback_max_tokens), 128)
        fallback_tokens = min(fallback_tokens, primary_tokens)
        if fallback_tokens < primary_tokens:
            return [primary_tokens, fallback_tokens]
        return [primary_tokens]

    def _build_vertex_payload(
        self,
        *,
        model: str,
        prompt: str,
        system: Optional[str],
        images: Optional[List[str]],
        num_predict: int,
        stream: bool,
    ) -> dict:
        messages: list[dict] = []
        if system:
            messages.append({
                "role": "system",
                "content": system,
            })

        user_content: Union[str, List[dict]]
        if images:
            user_content = [{"type": "text", "text": prompt}]
            for image in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": self._to_data_url(image),
                    },
                })
        else:
            user_content = prompt

        messages.append({
            "role": "user",
            "content": user_content,
        })

        # In Vertex endpoint mode we prefer the endpoint's configured model.
        # This avoids sending stale local model names when endpoint IDs change.
        selected_model = (settings.vertex_ai_model or "").strip() or model or settings.medical_model

        payload = {
            "model": selected_model,
            "messages": messages,
            "max_tokens": num_predict,
            "temperature": settings.vertex_ai_temperature,
            "stream": stream,
        }
        return payload

    def _build_openai_compatible_payload(
        self,
        *,
        model: str,
        prompt: str,
        system: Optional[str],
        images: Optional[List[str]],
        num_predict: int,
        stream: bool,
        include_system_role: bool = True,
    ) -> dict:
        messages: list[dict] = []
        effective_prompt = prompt
        if include_system_role and system:
            messages.append({
                "role": "system",
                "content": system,
            })
        elif system:
            effective_prompt = self._merge_system_into_user_prompt(system, prompt)

        user_content: Union[str, List[dict]]
        if images:
            user_content = [{"type": "text", "text": effective_prompt}]
            for image in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": self._to_data_url(image),
                    },
                })
        else:
            user_content = effective_prompt

        messages.append({
            "role": "user",
            "content": user_content,
        })

        selected_model = (
            (model or "").strip()
            or (settings.openai_compatible_model or "").strip()
            or settings.medical_model
        )
        if not selected_model:
            raise RuntimeError(
                "OpenAI-compatible route requires OPENAI_COMPATIBLE_MODEL or MEDICAL_MODEL"
            )

        return {
            "model": selected_model,
            "messages": messages,
            "max_tokens": num_predict,
            "temperature": settings.openai_compatible_temperature,
            "stream": stream,
        }

    @staticmethod
    def _merge_system_into_user_prompt(system: Optional[str], prompt: str) -> str:
        system_text = (system or "").strip()
        if not system_text:
            return prompt
        user_text = (prompt or "").strip()
        if not user_text:
            return system_text
        return f"{system_text}\n\nUser request:\n{user_text}"

    @staticmethod
    def _to_data_url(image_base64: str) -> str:
        if image_base64.startswith("data:"):
            return image_base64
        return f"data:image/jpeg;base64,{image_base64}"

    @staticmethod
    def _strip_thinking_tokens(text: str) -> str:
        """
        Remove chain-of-thought / scratchpad tokens from model output.

        MedGemma 27B and similar reasoning models emit internal thinking
        content that should NOT be shown to end users. Common patterns:

        1. XML-style:  <think>...</think> (may be multi-line)
        2. Inline scratchpad that starts with the literal word "thought" and
           ends with a marker like "Strategizing complete." — the real answer
           lives after the marker.
        3. Standalone scratchpad sections (Mental Sandbox Simulation, etc.)
           that appear anywhere in the text.

        This method strips all such content and returns only the final answer.
        """
        if not text:
            return text

        # Pattern 1: <think>...</think> blocks (non-greedy, handles multi-line).
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)

        # Pattern 2: Full scratchpad block starting with "thought".
        # The scratchpad ends at the LAST occurrence of known end-of-thinking
        # markers. Everything after the marker is the real answer.
        if re.match(r"^thought", text, flags=re.IGNORECASE):
            # End-of-thinking markers (ordered from most to least specific).
            end_markers = [
                r"Strategizing complete\.?\s*",
                r"Key Learnings:.*?\n\n",  # greedy to end of block
                r"Mental Sandbox Simulation:.*?\n\n",
            ]
            stripped = None
            for marker in end_markers:
                # Find the LAST match so we skip the entire scratchpad.
                matches = list(re.finditer(marker, text, flags=re.IGNORECASE | re.DOTALL))
                if matches:
                    end_pos = matches[-1].end()
                    candidate = text[end_pos:].lstrip()
                    if candidate:
                        stripped = candidate
                        break

            if stripped:
                text = stripped
            else:
                # Fallback: strip everything up to the first blank line.
                first_break = re.search(r"\n\n", text)
                if first_break:
                    text = text[first_break.end():].lstrip()

        # Pattern 3: Remove any remaining standalone scratchpad sections
        # that might appear after an already-partial strip or in other positions.
        text = re.sub(
            r"Mental Sandbox Simulation:[\s\S]*?(?=\n\n|$)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"Key Learnings:[\s\S]*?(?=\n\n|$)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"Strategizing complete\.?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        # Remove "Constraint Checklist & Confidence Score" blocks
        text = re.sub(
            r"\*?\*?Constraint Checklist[\s\S]*?(?=\n\n|$)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return text.strip()

    @staticmethod
    def _extract_vertex_text(payload: dict) -> str:
        if not isinstance(payload, dict):
            raise RuntimeError("Vertex AI response is not a JSON object")

        # OpenAI-compatible response shape.
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return LLMClient._strip_thinking_tokens(content)
                    if isinstance(content, list):
                        parts: list[str] = []
                        for item in content:
                            if isinstance(item, dict):
                                text = item.get("text")
                                if text:
                                    parts.append(str(text))
                        if parts:
                            return LLMClient._strip_thinking_tokens("".join(parts))

        # Fallback for non-standard response wrappers.
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return LLMClient._strip_thinking_tokens(output_text)

        raise RuntimeError("Vertex AI response did not include completion text")

    async def _vertex_headers(self) -> dict:
        token = await self._get_vertex_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        project = (settings.vertex_ai_project_id or "").strip()
        if project:
            headers["x-goog-user-project"] = project
        return headers

    def _openai_compatible_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        api_key = (settings.openai_compatible_api_key or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def _get_vertex_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        async with self._token_lock:
            now = time.time()
            if self._access_token and now < self._token_expires_at:
                return self._access_token

            auth_method = (settings.vertex_ai_auth_method or "auto").strip().lower()
            if auth_method not in {"auto", "adc", "gcloud"}:
                raise RuntimeError(
                    f"Unsupported VERTEX_AI_AUTH_METHOD='{auth_method}'. Use: auto, adc, or gcloud."
                )

            adc_error: Optional[Exception] = None
            if auth_method in {"auto", "adc"}:
                try:
                    token, expiry = await asyncio.to_thread(self._get_vertex_access_token_via_adc)
                    self._access_token = token
                    self._token_expires_at = expiry
                    return token
                except Exception as exc:
                    adc_error = exc
                    if auth_method == "adc":
                        raise RuntimeError(f"Failed to get Vertex access token via ADC: {exc}") from exc
                    logger.warning("Vertex ADC auth failed; falling back to gcloud. Details: %s", exc)

            if auth_method in {"auto", "gcloud"}:
                try:
                    token, expiry = await asyncio.to_thread(self._get_vertex_access_token_via_gcloud)
                    self._access_token = token
                    self._token_expires_at = expiry
                    return token
                except Exception as exc:
                    if auth_method == "gcloud":
                        raise
                    if adc_error:
                        raise RuntimeError(
                            "Failed to get Vertex access token via both ADC and gcloud. "
                            f"ADC error: {adc_error}; gcloud error: {exc}"
                        ) from exc
                    raise

            raise RuntimeError("Unable to acquire Vertex access token")

    def _get_vertex_access_token_via_adc(self) -> tuple[str, float]:
        """
        Resolve ADC credentials and refresh an OAuth access token.

        Credential lookup order:
        1) VERTEX_AI_SERVICE_ACCOUNT_JSON_BASE64
        2) VERTEX_AI_SERVICE_ACCOUNT_JSON
        3) GOOGLE_APPLICATION_CREDENTIALS / application default credentials
        """
        try:
            import google.auth
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing dependency 'google-auth'. Add it to requirements to use Vertex ADC authentication."
            ) from exc

        scopes = self._vertex_token_scopes()
        inline_sa = self._load_inline_service_account_info()
        if inline_sa:
            creds = service_account.Credentials.from_service_account_info(inline_sa, scopes=scopes)
        else:
            creds, _ = google.auth.default(scopes=scopes)

        creds.refresh(Request())
        token = (creds.token or "").strip()
        if not token:
            raise RuntimeError("ADC returned an empty access token")

        expires_at = getattr(creds, "expiry", None)
        if expires_at is not None:
            expires_epoch = float(expires_at.timestamp())
            return token, max(expires_epoch - 60.0, time.time() + 30.0)

        ttl = max(int(settings.vertex_ai_token_ttl_seconds), 60)
        return token, time.time() + max(ttl - 60, 30)

    def _get_vertex_access_token_via_gcloud(self) -> tuple[str, float]:
        command = (settings.vertex_ai_gcloud_command or "gcloud").strip() or "gcloud"
        argv = self._resolve_gcloud_argv(command)
        argv.extend(["auth", "print-access-token"])

        try:
            stdout, stderr, returncode = self._run_subprocess_capture(argv)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"gcloud CLI not found (command: {command}). "
                "Install Google Cloud CLI and run: gcloud auth login"
            ) from exc

        if returncode != 0:
            err = (stderr or "").strip()
            raise RuntimeError(
                f"Failed to get gcloud access token (exit {returncode}): {err or 'unknown error'}"
            )

        token = (stdout or "").strip()
        if not token:
            raise RuntimeError("gcloud returned an empty access token")

        ttl = max(int(settings.vertex_ai_token_ttl_seconds), 60)
        return token, time.time() + max(ttl - 60, 30)

    @staticmethod
    def _vertex_token_scopes() -> list[str]:
        raw_scopes = (settings.vertex_ai_token_scopes or "").strip()
        scopes = [s.strip() for s in raw_scopes.split(",") if s.strip()]
        if scopes:
            return scopes
        return ["https://www.googleapis.com/auth/cloud-platform"]

    @staticmethod
    def _load_inline_service_account_info() -> Optional[dict]:
        raw_base64 = (settings.vertex_ai_service_account_json_base64 or "").strip()
        if raw_base64:
            try:
                decoded = base64.b64decode(raw_base64).decode("utf-8")
                return json.loads(decoded)
            except Exception as exc:
                raise RuntimeError(
                    "VERTEX_AI_SERVICE_ACCOUNT_JSON_BASE64 is set but invalid base64/json."
                ) from exc

        raw_json = (settings.vertex_ai_service_account_json or "").strip()
        if raw_json:
            try:
                return json.loads(raw_json)
            except json.JSONDecodeError as exc:
                raise RuntimeError("VERTEX_AI_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc

        return None

    @staticmethod
    def _run_subprocess_capture(argv: List[str]) -> tuple[str, str, int]:
        """Run a subprocess synchronously (threaded by caller) and capture text output."""
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return completed.stdout or "", completed.stderr or "", int(completed.returncode)

    @staticmethod
    def _resolve_gcloud_argv(command: str) -> List[str]:
        """Resolve gcloud executable, including common Windows install locations."""
        argv = shlex.split(command, posix=False)
        if not argv:
            argv = ["gcloud"]

        executable = argv[0]
        normalized = executable.lower()
        if normalized in {"gcloud", "gcloud.cmd", "gcloud.exe"}:
            resolved = (
                shutil.which(executable)
                or shutil.which("gcloud.cmd")
                or shutil.which("gcloud.exe")
            )
            if not resolved:
                user_profile = os.environ.get("USERPROFILE", "")
                candidates = [
                    os.path.join(
                        user_profile,
                        "AppData",
                        "Local",
                        "Google",
                        "Cloud SDK",
                        "google-cloud-sdk",
                        "bin",
                        "gcloud.cmd",
                    ),
                    r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
                ]
                for candidate in candidates:
                    if candidate and os.path.exists(candidate):
                        resolved = candidate
                        break
            if resolved:
                argv[0] = resolved

        return argv

    async def embed(
        self,
        text: str,
        model: str = None,
        *,
        task_type: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embedding vector.

        Default behavior uses deterministic local hash embeddings so the system
        works without a separate embedding service.
        """
        model = model or settings.embedding_model

        if self._embedding_provider == "hash":
            return self._hash_embedding(text, settings.embedding_dimensions)

        if self._embedding_provider == "ollama":
            return await self._embed_ollama(text, model)

        if self._embedding_provider == "gemini":
            gemini_model = (model or "").strip()
            if not gemini_model or gemini_model == "nomic-embed-text":
                gemini_model = "gemini-embedding-001"
                logger.info(
                    "Embedding provider is gemini; defaulting EMBEDDING_MODEL to %s",
                    gemini_model,
                )
            gemini_api_key = (settings.gemini_api_key or "").strip()
            if gemini_api_key:
                return await self._embed_gemini_api(text, gemini_model, task_type=task_type)
            logger.info(
                "GEMINI_API_KEY not set; falling back to Vertex Gemini embedding route."
            )
            return await self._embed_gemini_vertex(text, gemini_model, task_type=task_type)

        raise RuntimeError(
            f"Unsupported embedding provider '{self._embedding_provider}'. "
            "Use 'hash', 'ollama', or 'gemini'."
        )

    async def _embed_ollama(self, text: str, model: str) -> List[float]:
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
                f"{e.response.text[:300] if e.response.text else 'No response'}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    async def _embed_gemini_api(
        self,
        text: str,
        model: str,
        *,
        task_type: Optional[str] = None,
    ) -> List[float]:
        url = self._gemini_embedding_url(model)
        headers = self._gemini_headers()
        payload = self._build_gemini_embedding_payload(text, task_type=task_type)
        requested_dims = max(int(settings.embedding_dimensions), 0)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                embedding = self._extract_vertex_embedding(response.json())
                if requested_dims and len(embedding) != requested_dims:
                    logger.warning(
                        "Gemini embedding dimension mismatch: expected=%s actual=%s model=%s",
                        requested_dims,
                        len(embedding),
                        model,
                    )
                return embedding
        except httpx.ConnectError:
            raise RuntimeError("Cannot connect to Gemini embeddings endpoint")
        except httpx.TimeoutException:
            raise RuntimeError("Gemini embedding request timed out")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Gemini embedding error ({e.response.status_code}): "
                f"{self._extract_http_error(e.response)}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Gemini embedding failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    async def _embed_gemini_vertex(
        self,
        text: str,
        model: str,
        *,
        task_type: Optional[str] = None,
    ) -> List[float]:
        url = self._vertex_embedding_url(model)
        headers = await self._vertex_headers()
        payload = self._build_vertex_embedding_payload(text, task_type=task_type)
        requested_dims = max(int(settings.embedding_dimensions), 0)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                embedding = self._extract_vertex_embedding(response.json())

                if requested_dims and len(embedding) != requested_dims:
                    logger.warning(
                        "Gemini embedding dimension mismatch: expected=%s actual=%s model=%s",
                        requested_dims,
                        len(embedding),
                        model,
                    )
                return embedding
        except httpx.ConnectError:
            raise RuntimeError("Cannot connect to Vertex Gemini embedding endpoint")
        except httpx.TimeoutException:
            raise RuntimeError("Vertex Gemini embedding request timed out")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Vertex Gemini embedding error ({e.response.status_code}): "
                f"{self._extract_http_error(e.response)}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Vertex Gemini embedding failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

    def _gemini_embedding_url(self, model: str) -> str:
        model_ref = (model or "").strip()
        if not model_ref:
            raise RuntimeError(
                "Embedding model is required. Set EMBEDDING_MODEL (for example: gemini-embedding-001)."
            )
        clean_model = model_ref
        if clean_model.startswith("models/"):
            clean_model = clean_model.split("/", 1)[1]

        base = self._normalize_vertex_host(settings.gemini_embedding_api_base or "")
        version = (settings.gemini_embedding_api_version or "v1beta").strip().strip("/")
        return f"{base}/{version}/models/{clean_model}:embedContent"

    def _build_gemini_embedding_payload(
        self,
        text: str,
        *,
        task_type: Optional[str] = None,
    ) -> dict:
        payload: dict = {
            "content": {
                "parts": [{"text": text or ""}],
            },
            "taskType": (
                task_type
                or settings.embedding_task_type_document
                or "RETRIEVAL_DOCUMENT"
            ),
        }

        requested_dims = max(int(settings.embedding_dimensions), 0)
        if requested_dims:
            payload["outputDimensionality"] = requested_dims

        return payload

    def _gemini_headers(self) -> dict:
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            raise RuntimeError("Gemini embedding route requires GEMINI_API_KEY")
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

    def _vertex_embedding_url(self, model: str) -> str:
        project = (settings.vertex_ai_project_id or "").strip()
        location = (settings.vertex_ai_location or "").strip()
        if not project or not location:
            raise RuntimeError(
                "Gemini embeddings require VERTEX_AI_PROJECT_ID and VERTEX_AI_LOCATION"
            )

        model_ref = (model or "").strip()
        if not model_ref:
            raise RuntimeError(
                "Embedding model is required. Set EMBEDDING_MODEL (for example: gemini-embedding-001)."
            )

        base = f"https://{location}-aiplatform.googleapis.com/v1"
        if model_ref.startswith("projects/"):
            resource = model_ref
        elif model_ref.startswith("publishers/"):
            resource = f"projects/{project}/locations/{location}/{model_ref}"
        else:
            resource = (
                f"projects/{project}/locations/{location}/publishers/google/models/{model_ref}"
            )

        if resource.endswith(":predict"):
            return f"{base}/{resource}"
        return f"{base}/{resource}:predict"

    def _build_vertex_embedding_payload(
        self,
        text: str,
        *,
        task_type: Optional[str] = None,
    ) -> dict:
        payload: dict = {
            "instances": [{
                "content": text or "",
                "task_type": (
                    task_type
                    or settings.embedding_task_type_document
                    or "RETRIEVAL_DOCUMENT"
                ),
            }]
        }

        requested_dims = max(int(settings.embedding_dimensions), 0)
        if requested_dims:
            payload["parameters"] = {"outputDimensionality": requested_dims}

        return payload

    @staticmethod
    def _hash_embedding(text: str, dims: int) -> List[float]:
        dim = max(int(dims), 8)
        vec = [0.0] * dim
        if not text:
            vec[0] = 1.0
            return vec

        # Word hashing with signed accumulation.
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            vec[idx] += sign * weight

        norm = sum(v * v for v in vec) ** 0.5
        if norm <= 1e-12:
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    async def _request_embedding(
        self,
        client: httpx.AsyncClient,
        text: str,
        model: str,
    ) -> List[float]:
        """
        Request embeddings with Ollama endpoint compatibility.

        Tries /api/embeddings first, then falls back to /api/embed if needed.
        """
        response = await client.post(
            f"{self.host}/api/embeddings",
            json={
                "model": model,
                "prompt": text,
            },
        )

        if response.status_code == 404 and not self._is_model_missing_error(response, model):
            response = await client.post(
                f"{self.host}/api/embed",
                json={
                    "model": model,
                    "input": text,
                },
            )

        response.raise_for_status()
        return self._extract_embedding(response.json())

    @staticmethod
    def _extract_embedding(payload: dict) -> List[float]:
        embedding = payload.get("embedding")
        if isinstance(embedding, list) and embedding:
            return embedding

        embeddings = payload.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, list):
                return first
            if isinstance(first, (int, float)):
                return embeddings

        raise RuntimeError("Ollama embedding response is missing embedding vector")

    @staticmethod
    def _extract_vertex_embedding(payload: dict) -> List[float]:
        if not isinstance(payload, dict):
            raise RuntimeError("Vertex Gemini embedding response is not a JSON object")

        predictions = payload.get("predictions")
        if isinstance(predictions, list) and predictions:
            first = predictions[0]
            if isinstance(first, dict):
                embedded = first.get("embeddings")
                if isinstance(embedded, dict):
                    values = LLMClient._extract_numeric_list(embedded.get("values"))
                    if values:
                        return values

                values = LLMClient._extract_numeric_list(first.get("values"))
                if values:
                    return values

                values = LLMClient._extract_numeric_list(first.get("embedding"))
                if values:
                    return values

        values = LLMClient._extract_numeric_list(
            (payload.get("embedding") or {}).get("values")
            if isinstance(payload.get("embedding"), dict)
            else payload.get("embedding")
        )
        if values:
            return values

        values = LLMClient._extract_numeric_list(
            (payload.get("data") or [{}])[0].get("embedding")
            if isinstance(payload.get("data"), list) and payload.get("data")
            else None
        )
        if values:
            return values

        raise RuntimeError("Vertex Gemini embedding response is missing embedding vector")

    @staticmethod
    def _extract_numeric_list(value: object) -> List[float]:
        if not isinstance(value, list) or not value:
            return []
        if not all(isinstance(item, (int, float)) for item in value):
            return []
        return [float(item) for item in value]

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                value = payload.get("error")
                if value:
                    return str(value)
        except Exception:
            pass
        return response.text or ""

    @staticmethod
    def _extract_http_error(response: httpx.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                for key in ("error", "message", "detail"):
                    val = data.get(key)
                    if val:
                        return str(val)[:300]
        except Exception:
            pass
        text = (response.text or "").strip()
        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" in content_type or text.lower().startswith("<!doctype html") or "<html" in text.lower()[:80]:
            return "Upstream gateway returned an HTML error page"
        return (text or "No response")[:300]

    @staticmethod
    def _is_role_alternation_error(error_text: str) -> bool:
        text = (error_text or "").strip().lower()
        return bool(text) and "roles must alternate" in text

    def _is_model_missing_error(self, response: httpx.Response, model: str) -> bool:
        message = self._extract_error_message(response).lower()
        if response.status_code != 404 or "not found" not in message or "model" not in message:
            return False
        model_lower = model.lower()
        return model_lower in message or f"\"{model_lower}\"" in message

    async def embed_batch(
        self,
        texts: List[str],
        model: str = None,
        *,
        task_type: Optional[str] = None,
    ) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding = await self.embed(text, model, task_type=task_type)
            embeddings.append(embedding)
        return embeddings

    async def unload(self, model: str) -> bool:
        """
        Unload a model from memory.

        Vertex is remote, so this is a no-op and always succeeds.
        """
        if self._provider != "ollama":
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": model,
                        "keep_alive": 0,
                    },
                )
                response.raise_for_status()
                self._loaded_model = None
                return True
        except Exception:
            return False

    async def list_models(self) -> List[dict]:
        """List available models."""
        if self._provider == "ollama":
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.host}/api/tags")
                response.raise_for_status()
                return response.json().get("models", [])

        if is_openai_compatible_provider(self._provider):
            model_name = settings.openai_compatible_model or settings.medical_model
            return [{"name": model_name}] if model_name else []

        model_name = settings.vertex_ai_model or settings.medical_model
        return [{"name": model_name}] if model_name else []

    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama registry.

        Vertex mode does not support pull and simply checks configured availability.
        """
        if self._provider != "ollama":
            return await self.check_model_available(model)

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
                f"{e.response.text[:300] if e.response.text else 'No response'}"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama pull failed: {type(e).__name__}: {str(e) or 'Unknown error'}")

        return await self.check_model_available(model)

    async def ensure_model_available(self, model: str) -> bool:
        """Ensure a model is available locally, pulling it if needed."""
        if self._provider != "ollama":
            return await self.check_model_available(model)

        if await self.check_model_available(model):
            return True

        lock = self._model_locks.setdefault(model, asyncio.Lock())
        async with lock:
            if await self.check_model_available(model):
                return True
            return await self.pull_model(model)

    async def check_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        if model == settings.embedding_model:
            if self._embedding_provider == "hash":
                return True
            if self._embedding_provider == "gemini":
                if (settings.gemini_api_key or "").strip():
                    return bool((settings.embedding_model or "").strip())
                project = bool((settings.vertex_ai_project_id or "").strip())
                location = bool((settings.vertex_ai_location or "").strip())
                return project and location and bool((settings.embedding_model or "").strip())
            if self._embedding_provider == "ollama":
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                        response = await client.get(f"{self.host}/api/tags")
                        response.raise_for_status()
                        models = response.json().get("models", [])
                        model_names = [m.get("name", "") for m in models]
                        return any(
                            name == model or name.startswith(f"{model}:")
                            for name in model_names
                        )
                except Exception:
                    return False

        if is_openai_compatible_provider(self._provider):
            requested_model = (model or "").strip()
            configured_model = (settings.openai_compatible_model or settings.medical_model or "").strip()
            effective_model = requested_model or configured_model
            base_url = bool((settings.openai_compatible_base_url or "").strip())
            if requested_model and configured_model and requested_model != configured_model:
                logger.warning(
                    "Requested model '%s' differs from configured OpenAI-compatible model '%s'.",
                    requested_model,
                    configured_model,
                )
            return base_url and bool(effective_model)

        if self._provider != "ollama":
            project = bool((settings.vertex_ai_project_id or "").strip())
            location = bool((settings.vertex_ai_location or "").strip())
            endpoint_id = bool((settings.vertex_ai_endpoint_id or "").strip())
            model_name = (settings.vertex_ai_model or settings.medical_model or "").strip()
            if model and model_name and model != model_name:
                # Same endpoint is currently used for both medical and verification calls.
                logger.warning(
                    "Requested model '%s' differs from configured Vertex model '%s'.",
                    model,
                    model_name,
                )
            return project and location and endpoint_id and bool(model_name)

        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        return any(
            name == model or name.startswith(f"{model}:")
            for name in model_names
        )

    async def health_check(self) -> bool:
        """Check whether configured LLM provider is reachable."""
        if not await self.check_model_available(settings.medical_model):
            return False

        if self._provider == "ollama":
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                    response = await client.get(f"{self.host}/api/tags")
                    return response.status_code == 200
            except Exception:
                return False

        try:
            if is_openai_compatible_provider(self._provider):
                _ = await self._generate_openai_compatible(
                    model=settings.medical_model,
                    prompt="Reply with: ok",
                    system="You are a health check assistant. Respond with exactly 'ok'.",
                    images=None,
                    num_predict=8,
                )
                return True

            _ = await self._generate_vertex(
                model=settings.medical_model,
                prompt="Reply with: ok",
                system="You are a health check assistant. Respond with exactly 'ok'.",
                images=None,
                num_predict=8,
            )
            return True
        except Exception as e:
            logger.warning("%s health check failed: %s", self._provider, e)
            return False


# Singleton instance (preferred name)
llm_client = LLMClient()

# Backward-compatible aliases (legacy naming)
OllamaClient = LLMClient
ollama_client = llm_client
