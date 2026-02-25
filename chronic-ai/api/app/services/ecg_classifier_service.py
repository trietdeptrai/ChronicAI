"""
ECG classifier service.

Pipeline:
1) Receive base64-encoded ECG image.
2) Call a remote ECG classifier endpoint (MedSigLIP + MoE).
3) Return per-class scores for downstream MedGemma analysis.

The endpoint runs the full pipeline: image → MedSigLIP embedding → classifier → scores.
This service only makes an HTTP call — no local PyTorch or transformers needed.

Supported auth types (via ECG_CLASSIFIER_AUTH_TYPE):
  - none:          No auth headers (local dev, VPN-protected endpoints)
  - bearer:        Static Authorization: Bearer <token>
  - api_key:       Configurable header + key (e.g. X-API-Key)
  - vertex_gcloud: GCP access token via gcloud CLI (default, backward-compat)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ECGClassifierService:
    """Calls a remote ECG classifier endpoint for predictions.

    Works with any HTTP endpoint that accepts ``{"image_base64": "..."}``
    and returns per-class scores.  Auth is controlled by
    ``ECG_CLASSIFIER_AUTH_TYPE`` (see module docstring).
    """

    def __init__(self) -> None:
        self._timeout = httpx.Timeout(
            float(settings.ecg_classifier_endpoint_timeout),
            connect=30.0,
        )

    def _get_endpoint_url(self) -> str:
        url = (settings.ecg_classifier_endpoint_url or "").strip()
        if not url:
            raise RuntimeError(
                "ECG classifier endpoint is not configured. "
                "Set ECG_CLASSIFIER_ENDPOINT_URL in your environment."
            )
        return url

    async def _get_auth_headers(self) -> dict[str, str]:
        """
        Build authentication headers based on the configured auth type.

        Supported types: none, bearer, api_key, vertex_gcloud.
        """
        auth_type = (settings.ecg_classifier_auth_type or "vertex_gcloud").strip().lower()

        if auth_type == "none":
            return {"Content-Type": "application/json"}

        if auth_type == "bearer":
            token = (settings.ecg_classifier_bearer_token or "").strip()
            if not token:
                raise RuntimeError(
                    "ECG_CLASSIFIER_BEARER_TOKEN is required when "
                    "ECG_CLASSIFIER_AUTH_TYPE=bearer"
                )
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

        if auth_type == "api_key":
            key = (settings.ecg_classifier_api_key or "").strip()
            header_name = (
                settings.ecg_classifier_api_key_header or "X-API-Key"
            ).strip()
            if not key:
                raise RuntimeError(
                    "ECG_CLASSIFIER_API_KEY is required when "
                    "ECG_CLASSIFIER_AUTH_TYPE=api_key"
                )
            return {
                header_name: key,
                "Content-Type": "application/json",
            }

        if auth_type == "vertex_gcloud":
            from app.services.llm_client import llm_client

            token = await llm_client._get_vertex_access_token()
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

        raise RuntimeError(
            f"Unsupported ECG_CLASSIFIER_AUTH_TYPE='{auth_type}'. "
            "Use: none, bearer, api_key, or vertex_gcloud."
        )

    async def predict_from_base64(self, image_base64: str) -> dict[str, Any]:
        """
        Call the remote ECG classifier endpoint and return per-class scores.

        The response format matches the previous local implementation so that
        downstream code in llm.py requires no changes.
        """
        start_total = time.perf_counter()
        logger.info(
            "[ecg-classifier] predict start (remote) image_base64_len=%s",
            len(image_base64 or ""),
        )

        endpoint_url = self._get_endpoint_url()

        # Build request payload
        request_body = {"image_base64": image_base64}

        # Check if endpoint uses Vertex AI prediction format
        # (wraps payload in {"instances": [...]})
        is_vertex_predict = endpoint_url.rstrip("/").endswith(":predict")
        if is_vertex_predict:
            request_body = {"instances": [request_body]}

        try:
            headers = await self._get_auth_headers()

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    endpoint_url,
                    headers=headers,
                    json=request_body,
                )
                response.raise_for_status()
                result = response.json()

        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to ECG classifier endpoint: {endpoint_url}"
            )
        except httpx.TimeoutException:
            raise RuntimeError("ECG classifier endpoint request timed out")
        except httpx.HTTPStatusError as exc:
            error_detail = ""
            try:
                error_detail = exc.response.text[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"ECG classifier endpoint error ({exc.response.status_code}): {error_detail}"
            )

        # Parse response — handle both direct and Vertex AI prediction wrapper formats
        prediction = result
        if "predictions" in result and isinstance(result["predictions"], list):
            # Vertex AI wraps the response: {"predictions": [{...}]}
            predictions = result["predictions"]
            if predictions:
                prediction = predictions[0]
            else:
                raise RuntimeError("ECG classifier endpoint returned empty predictions.")

        # Extract fields (matching the format from serve.py)
        classes = [str(c) for c in prediction.get("classes", [])]
        scores = [float(s) for s in prediction.get("scores", [])]
        scores_by_class = {
            str(k): float(v)
            for k, v in prediction.get("scores_by_class", {}).items()
        }
        predicted_labels = [str(l) for l in prediction.get("predicted_labels", [])]
        threshold = float(prediction.get("threshold", 0.5))
        classifier_type = str(prediction.get("classifier_type", ""))
        medsiglip_model_id = str(prediction.get("medsiglip_model_id", ""))

        elapsed_ms = (time.perf_counter() - start_total) * 1000
        logger.info(
            "[ecg-classifier] predict complete (remote) classifier_type=%s predicted=%s "
            "top3=%s elapsed_ms=%.1f",
            classifier_type,
            predicted_labels,
            sorted(scores_by_class.items(), key=lambda x: x[1], reverse=True)[:3],
            elapsed_ms,
        )

        return {
            "classifier_type": classifier_type,
            "checkpoint_path": "vertex-ai-endpoint",
            "medsiglip_model_id": medsiglip_model_id,
            "classes": classes,
            "scores": scores,
            "scores_by_class": scores_by_class,
            "predicted_labels": predicted_labels,
            "threshold": threshold,
        }


ecg_classifier_service = ECGClassifierService()
