"""
ECG Classifier Serving Container for Vertex AI.

Loads MedSigLIP (google/medsiglip-448) + MoE/MLP classifier checkpoint
and serves predictions via HTTP.

Vertex AI will send:
  - POST requests to the inference route (default: /predict)
  - GET  requests to the health route (default: /health)

The model checkpoint is loaded from the path specified by the
AIP_STORAGE_URI environment variable (set by Vertex AI) or from
a local fallback path.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model architectures (must match training code)
# ---------------------------------------------------------------------------

class ExpertMLP(nn.Module):
    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        hidden: tuple[int, ...] = (1028, 512, 256),
        dropout: tuple[float, ...] = (0.15, 0.15, 0.10),
    ):
        super().__init__()
        layers: list[nn.Module] = []
        prev = in_dim
        dropout_values = tuple(float(p) for p in dropout)
        if len(dropout_values) < len(hidden):
            dropout_values = dropout_values + (0.0,) * (len(hidden) - len(dropout_values))
        elif len(dropout_values) > len(hidden):
            dropout_values = dropout_values[: len(hidden)]
        for h, p in zip(hidden, dropout_values):
            layers.append(nn.Linear(prev, h))
            layers.append(nn.LayerNorm(h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(p))
            prev = h
        layers.append(nn.Linear(prev, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MoEClassifier(nn.Module):
    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        num_experts: int = 5,
        gate_hidden: int = 512,
        temperature: float = 1.0,
        expert_hidden: tuple[int, ...] = (1028, 512, 256),
        expert_dropout: tuple[float, ...] = (0.15, 0.15, 0.10),
    ):
        super().__init__()
        self.temperature = temperature
        self.experts = nn.ModuleList(
            [
                ExpertMLP(in_dim, out_dim, hidden=expert_hidden, dropout=expert_dropout)
                for _ in range(num_experts)
            ]
        )
        self.gate = nn.Sequential(
            nn.Linear(in_dim, gate_hidden),
            nn.ReLU(),
            nn.Linear(gate_hidden, num_experts),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        gate_logits = self.gate(x) / self.temperature
        gate_w = torch.softmax(gate_logits, dim=-1)
        expert_logits = torch.stack([expert(x) for expert in self.experts], dim=1)
        mixed_logits = torch.sum(expert_logits * gate_w.unsqueeze(-1), dim=1)
        return mixed_logits, gate_w, expert_logits


class MLPClassifier(nn.Module):
    def __init__(self, in_dim: int, hidden_1: int, hidden_2: int, out_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_1)
        self.fc2 = nn.Linear(hidden_1, hidden_2)
        self.out = nn.Linear(hidden_2, out_dim)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.out(x)


# ---------------------------------------------------------------------------
# Checkpoint loading
# ---------------------------------------------------------------------------

def build_classifier(ckpt: dict[str, Any]) -> tuple[nn.Module, str]:
    """Reconstruct classifier architecture from checkpoint metadata."""
    state_dict = ckpt.get("state_dict")
    if not isinstance(state_dict, dict) or not state_dict:
        raise RuntimeError("Checkpoint missing state_dict.")

    embed_dim = int(ckpt["embed_dim"])
    num_classes = int(ckpt["num_classes"])

    if any(key.startswith("experts.") for key in state_dict):
        num_experts = int(ckpt.get("num_experts", 5))
        expert_linear_layers: list[tuple[int, torch.Tensor]] = []
        for key, value in state_dict.items():
            if (
                key.startswith("experts.0.net.")
                and key.endswith(".weight")
                and isinstance(value, torch.Tensor)
                and value.ndim == 2
            ):
                layer_index = int(key.split(".")[3])
                expert_linear_layers.append((layer_index, value))

        if len(expert_linear_layers) < 2:
            raise RuntimeError("Unable to infer expert architecture from checkpoint.")

        expert_linear_layers.sort(key=lambda item: item[0])
        expert_hidden = tuple(int(w.shape[0]) for _, w in expert_linear_layers[:-1])
        gate_hidden = (
            int(state_dict["gate.0.weight"].shape[0])
            if "gate.0.weight" in state_dict
            else 256
        )
        model = MoEClassifier(
            in_dim=embed_dim,
            out_dim=num_classes,
            num_experts=num_experts,
            gate_hidden=gate_hidden,
            temperature=1.0,
            expert_hidden=expert_hidden,
            expert_dropout=tuple(0.0 for _ in expert_hidden),
        )
        model_type = "moe"
    elif {"fc1.weight", "fc2.weight", "out.weight"}.issubset(state_dict):
        hidden_1 = int(state_dict["fc1.weight"].shape[0])
        hidden_2 = int(state_dict["fc2.weight"].shape[0])
        model = MLPClassifier(embed_dim, hidden_1, hidden_2, num_classes)
        model_type = "mlp"
    else:
        raise RuntimeError("Unsupported checkpoint format.")

    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model, model_type


def extract_features(output: Any) -> torch.Tensor:
    """Extract image features from MedSigLIP output."""
    if isinstance(output, torch.Tensor):
        return output
    if hasattr(output, "pooler_output") and output.pooler_output is not None:
        return output.pooler_output
    if hasattr(output, "last_hidden_state") and output.last_hidden_state is not None:
        return output.last_hidden_state[:, 0, :]
    raise TypeError(f"Unexpected feature output type: {type(output)}")


# ---------------------------------------------------------------------------
# Global model state (loaded once at startup)
# ---------------------------------------------------------------------------

_embedder = None
_processor = None
_classifier = None
_classifier_type = ""
_device = "cpu"
_classes: list[str] = []
_threshold: float = 0.5
_model_id = ""
_embed_dim = 0


def _resolve_checkpoint_path() -> Path:
    """
    Find the checkpoint file.

    Priority:
    1. AIP_STORAGE_URI (set by Vertex AI) — the GCS model artifact directory
    2. CHECKPOINT_PATH env var (local dev fallback)
    3. Default path relative to this script
    """
    # Vertex AI mounts GCS artifacts here
    storage_uri = os.environ.get("AIP_STORAGE_URI", "").strip()
    if storage_uri:
        # Vertex AI downloads GCS artifacts to a local directory
        # Look for .pt files in the directory
        storage_path = Path(storage_uri)
        if storage_path.is_dir():
            pt_files = list(storage_path.glob("*.pt"))
            if pt_files:
                return pt_files[0]

    # Local fallback
    local_path = os.environ.get("CHECKPOINT_PATH", "").strip()
    if local_path:
        return Path(local_path)

    # Default: look next to this script
    default = Path(__file__).parent.parent / "embed_data" / "moe_classifier_medsiglip.pt"
    return default


def load_models():
    """Load MedSigLIP embedder + classifier at startup."""
    global _embedder, _processor, _classifier, _classifier_type
    global _device, _classes, _threshold, _model_id, _embed_dim

    from transformers import AutoImageProcessor, AutoModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_id = os.environ.get("MEDSIGLIP_MODEL_ID", "google/medsiglip-448").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip() or None

    checkpoint_path = _resolve_checkpoint_path()
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    logger.info(
        "Loading models: model_id=%s checkpoint=%s device=%s",
        model_id,
        checkpoint_path,
        device,
    )

    # Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    if not isinstance(ckpt, dict):
        raise RuntimeError("Invalid checkpoint structure.")

    # Load MedSigLIP
    embedder = AutoModel.from_pretrained(model_id, token=hf_token)
    processor = AutoImageProcessor.from_pretrained(model_id, token=hf_token)
    embedder.to(device)
    embedder.eval()

    # Load classifier
    classifier, classifier_type = build_classifier(ckpt)
    classifier.to(device)
    classifier.eval()

    # Extract metadata
    num_classes = int(ckpt["num_classes"])
    classes = ckpt.get("classes")
    if not isinstance(classes, list) or len(classes) != num_classes:
        classes = [f"class_{i}" for i in range(num_classes)]

    _embedder = embedder
    _processor = processor
    _classifier = classifier
    _classifier_type = classifier_type
    _device = device
    _classes = [str(c) for c in classes]
    _threshold = float(ckpt.get("threshold", 0.5))
    _model_id = model_id
    _embed_dim = int(ckpt["embed_dim"])

    logger.info(
        "Models loaded: classifier_type=%s classes=%s embed_dim=%s threshold=%.3f device=%s",
        _classifier_type,
        _classes,
        _embed_dim,
        _threshold,
        _device,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="ECG Classifier", version="1.0.0")


@app.on_event("startup")
def startup():
    load_models()


class PredictRequest(BaseModel):
    image_base64: str


class PredictResponse(BaseModel):
    classifier_type: str
    medsiglip_model_id: str
    classes: list[str]
    scores: list[float]
    scores_by_class: dict[str, float]
    predicted_labels: list[str]
    threshold: float


@app.get("/health")
def health():
    """Health check for Vertex AI."""
    return {
        "status": "healthy" if _embedder is not None else "loading",
        "classifier_type": _classifier_type,
        "device": _device,
    }


@app.post("/predict", response_model=PredictResponse)
@torch.no_grad()
def predict(request: PredictRequest):
    """
    Classify an ECG image.

    Accepts a base64-encoded image, returns per-class sigmoid scores.
    """
    if _embedder is None or _processor is None or _classifier is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    start = time.perf_counter()

    # Decode image
    payload = (request.image_base64 or "").strip()
    if not payload:
        raise HTTPException(status_code=400, detail="image_base64 is empty.")
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        raw = base64.b64decode(payload)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    # Embed with MedSigLIP
    inputs = _processor(images=[image], return_tensors="pt")
    inputs = {k: v.to(_device) for k, v in inputs.items()}
    image_features = extract_features(_embedder.get_image_features(**inputs))

    if image_features.ndim != 2 or image_features.shape[0] != 1:
        raise HTTPException(status_code=500, detail=f"Unexpected embedding shape: {tuple(image_features.shape)}")
    if int(image_features.shape[1]) != _embed_dim:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding dim mismatch: expected={_embed_dim}, got={int(image_features.shape[1])}",
        )

    # Classify
    logits_output = _classifier(image_features)
    logits = logits_output[0] if isinstance(logits_output, tuple) else logits_output
    probs = torch.sigmoid(logits).squeeze(0).detach().cpu().tolist()
    scores = [float(s) for s in probs]

    scores_by_class = {label: score for label, score in zip(_classes, scores)}
    predicted_labels = [
        label for label, score in zip(_classes, scores) if score >= _threshold
    ]

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "predict: predicted=%s top3=%s elapsed_ms=%.1f",
        predicted_labels,
        sorted(scores_by_class.items(), key=lambda x: x[1], reverse=True)[:3],
        elapsed_ms,
    )

    return PredictResponse(
        classifier_type=_classifier_type,
        medsiglip_model_id=_model_id,
        classes=list(_classes),
        scores=scores,
        scores_by_class=scores_by_class,
        predicted_labels=predicted_labels,
        threshold=_threshold,
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("AIP_HTTP_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
