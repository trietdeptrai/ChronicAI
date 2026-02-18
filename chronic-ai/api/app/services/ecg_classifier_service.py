"""
ECG classifier service.

Pipeline:
1) Decode uploaded ECG image (base64).
2) Build MedSigLIP image embedding.
3) Run classifier checkpoint on embedding.
4) Return per-class scores for downstream MedGemma analysis.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

import torch
import torch.nn as nn
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class ExpertMLP(nn.Module):
    """Expert architecture used by the MoE classifier checkpoint."""

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
        hidden_dims = tuple(int(h) for h in hidden)
        dropout_values = tuple(float(p) for p in dropout)
        if len(dropout_values) < len(hidden_dims):
            dropout_values = dropout_values + (0.0,) * (len(hidden_dims) - len(dropout_values))
        elif len(dropout_values) > len(hidden_dims):
            dropout_values = dropout_values[:len(hidden_dims)]

        for h, p in zip(hidden_dims, dropout_values):
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
    """Soft mixture-of-experts classifier used for the default ECG checkpoint."""

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
                ExpertMLP(
                    in_dim=in_dim,
                    out_dim=out_dim,
                    hidden=expert_hidden,
                    dropout=expert_dropout,
                )
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
    """Simple MLP fallback architecture for legacy checkpoints."""

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


class ECGClassifierService:
    """Lazily loads MedSigLIP + ECG classifier, then serves per-image predictions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._embedder: Optional[Any] = None
        self._processor: Optional[Any] = None
        self._classifier: Optional[nn.Module] = None
        self._classifier_type: str = ""
        self._device: str = "cpu"
        self._embed_dim: int = 0
        self._classes: list[str] = []
        self._threshold: float = 0.5
        self._checkpoint_path: Optional[Path] = None
        self._model_id: str = ""

    def _resolve_device(self) -> str:
        requested = (settings.ecg_classifier_device or "auto").strip().lower()
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cuda" and not torch.cuda.is_available():
            logger.warning("ECG classifier requested CUDA but CUDA is unavailable. Falling back to CPU.")
            return "cpu"
        if requested not in {"cpu", "cuda"}:
            logger.warning("Unknown ECG classifier device '%s'. Falling back to auto.", requested)
            return "cuda" if torch.cuda.is_available() else "cpu"
        return requested

    def _resolve_checkpoint_path(self) -> Path:
        raw = (settings.ecg_classifier_checkpoint_path or "").strip()
        if not raw:
            raise RuntimeError("ECG classifier checkpoint path is empty.")
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        project_root = Path(__file__).resolve().parents[3]
        return (project_root / path).resolve()

    @staticmethod
    def _top_scores_for_log(
        classes: list[str],
        scores: list[float],
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        ranked = sorted(
            zip(classes, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return [(str(label), float(score)) for label, score in ranked[:top_k]]

    @staticmethod
    def _decode_base64_image(image_base64: str) -> Image.Image:
        payload = (image_base64 or "").strip()
        if not payload:
            raise ValueError("image_base64 is empty")
        if payload.startswith("data:") and "," in payload:
            payload = payload.split(",", 1)[1]
        raw = base64.b64decode(payload)
        return Image.open(io.BytesIO(raw)).convert("RGB")

    @staticmethod
    def _extract_features(output: Any) -> torch.Tensor:
        if isinstance(output, torch.Tensor):
            return output
        if hasattr(output, "pooler_output") and output.pooler_output is not None:
            return output.pooler_output
        if hasattr(output, "last_hidden_state") and output.last_hidden_state is not None:
            return output.last_hidden_state[:, 0, :]
        raise TypeError(f"Unexpected MedSigLIP feature output type: {type(output)}")

    @staticmethod
    def _build_classifier(ckpt: dict[str, Any]) -> tuple[nn.Module, str]:
        state_dict = ckpt.get("state_dict")
        if not isinstance(state_dict, dict) or not state_dict:
            raise RuntimeError("ECG classifier checkpoint is missing state_dict.")

        embed_dim = int(ckpt["embed_dim"])
        num_classes = int(ckpt["num_classes"])

        if any(key.startswith("experts.") for key in state_dict.keys()):
            num_experts = int(ckpt.get("num_experts", 5))
            expert_linear_layers: list[tuple[int, torch.Tensor]] = []
            for key, value in state_dict.items():
                if not (
                    key.startswith("experts.0.net.")
                    and key.endswith(".weight")
                    and isinstance(value, torch.Tensor)
                    and value.ndim == 2
                ):
                    continue
                # experts.0.net.<idx>.weight
                layer_index = int(key.split(".")[3])
                expert_linear_layers.append((layer_index, value))

            if len(expert_linear_layers) < 2:
                raise RuntimeError("Unable to infer expert MLP architecture from checkpoint.")

            expert_linear_layers.sort(key=lambda item: item[0])
            expert_hidden = tuple(int(weight.shape[0]) for _, weight in expert_linear_layers[:-1])
            gate_hidden = int(state_dict["gate.0.weight"].shape[0]) if "gate.0.weight" in state_dict else 256

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
        elif {"fc1.weight", "fc2.weight", "out.weight"}.issubset(state_dict.keys()):
            hidden_1 = int(state_dict["fc1.weight"].shape[0])
            hidden_2 = int(state_dict["fc2.weight"].shape[0])
            model = MLPClassifier(
                in_dim=embed_dim,
                hidden_1=hidden_1,
                hidden_2=hidden_2,
                out_dim=num_classes,
            )
            model_type = "mlp"
        else:
            raise RuntimeError("Unsupported ECG classifier checkpoint format.")

        model.load_state_dict(state_dict, strict=True)
        model.eval()
        return model, model_type

    def _ensure_loaded(self) -> None:
        if self._embedder is not None and self._processor is not None and self._classifier is not None:
            return

        with self._lock:
            if self._embedder is not None and self._processor is not None and self._classifier is not None:
                return

            checkpoint_path = self._resolve_checkpoint_path()
            if not checkpoint_path.exists():
                raise FileNotFoundError(f"ECG classifier checkpoint not found: {checkpoint_path}")

            ckpt = torch.load(checkpoint_path, map_location="cpu")
            if not isinstance(ckpt, dict):
                raise RuntimeError("Invalid ECG checkpoint structure.")

            model_id = (settings.ecg_medsiglip_model_id or "google/medsiglip-448").strip()
            if not model_id:
                model_id = "google/medsiglip-448"
            token = (settings.hf_token or "").strip() or None
            device = self._resolve_device()

            logger.info(
                "[ecg-classifier] loading model_id=%s ckpt=%s device=%s",
                model_id,
                str(checkpoint_path),
                device,
            )

            try:
                from transformers import AutoImageProcessor, AutoModel
            except Exception as exc:
                raise RuntimeError(
                    "Failed to import transformers image modules for ECG classifier."
                ) from exc

            embedder = AutoModel.from_pretrained(model_id, token=token)
            processor = AutoImageProcessor.from_pretrained(model_id, token=token)
            classifier, classifier_type = self._build_classifier(ckpt)

            embedder.to(device)
            embedder.eval()
            classifier.to(device)
            classifier.eval()

            num_classes = int(ckpt["num_classes"])
            classes = ckpt.get("classes")
            if not isinstance(classes, list) or len(classes) != num_classes:
                classes = [f"class_{idx}" for idx in range(num_classes)]

            self._embedder = embedder
            self._processor = processor
            self._classifier = classifier
            self._classifier_type = classifier_type
            self._device = device
            self._embed_dim = int(ckpt["embed_dim"])
            self._classes = [str(item) for item in classes]
            self._threshold = float(ckpt.get("threshold", 0.5))
            self._checkpoint_path = checkpoint_path
            self._model_id = model_id
            logger.info(
                "[ecg-classifier] loaded classifier_type=%s classes=%s embed_dim=%s threshold=%.3f",
                self._classifier_type,
                len(self._classes),
                self._embed_dim,
                self._threshold,
            )

    @torch.no_grad()
    def predict_from_base64(self, image_base64: str) -> dict[str, Any]:
        """Return ordered ECG classifier scores for one image."""
        start_total = time.perf_counter()
        logger.info(
            "[ecg-classifier] predict start image_base64_len=%s",
            len(image_base64 or ""),
        )
        self._ensure_loaded()

        if self._embedder is None or self._processor is None or self._classifier is None:
            raise RuntimeError("ECG classifier service failed to initialize.")

        image = self._decode_base64_image(image_base64)
        logger.info(
            "[ecg-classifier] image decoded size=%sx%s mode=%s",
            image.width,
            image.height,
            image.mode,
        )
        inputs = self._processor(images=[image], return_tensors="pt")
        inputs = {key: value.to(self._device) for key, value in inputs.items()}

        image_features = self._extract_features(self._embedder.get_image_features(**inputs))
        if image_features.ndim != 2 or image_features.shape[0] != 1:
            raise RuntimeError(f"Unexpected embedding shape: {tuple(image_features.shape)}")
        if int(image_features.shape[1]) != self._embed_dim:
            raise RuntimeError(
                f"Embedding dim mismatch: expected={self._embed_dim}, got={int(image_features.shape[1])}"
            )
        logger.info(
            "[ecg-classifier] embedding ready shape=%s device=%s",
            tuple(image_features.shape),
            self._device,
        )

        logits_output = self._classifier(image_features)
        logits = logits_output[0] if isinstance(logits_output, tuple) else logits_output
        probs = torch.sigmoid(logits).squeeze(0).detach().cpu().tolist()
        scores = [float(score) for score in probs]

        scores_by_class = {label: float(score) for label, score in zip(self._classes, scores)}
        predicted_labels = [
            label
            for label, score in zip(self._classes, scores)
            if float(score) >= float(self._threshold)
        ]
        top_scores = self._top_scores_for_log(self._classes, scores, top_k=3)
        elapsed_ms = (time.perf_counter() - start_total) * 1000
        logger.info(
            "[ecg-classifier] predict complete classifier_type=%s predicted=%s top3=%s elapsed_ms=%.1f",
            self._classifier_type,
            predicted_labels,
            top_scores,
            elapsed_ms,
        )

        return {
            "classifier_type": self._classifier_type,
            "checkpoint_path": str(self._checkpoint_path) if self._checkpoint_path else "",
            "medsiglip_model_id": self._model_id,
            "classes": list(self._classes),
            "scores": scores,
            "scores_by_class": scores_by_class,
            "predicted_labels": predicted_labels,
            "threshold": float(self._threshold),
        }


ecg_classifier_service = ECGClassifierService()
