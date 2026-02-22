"""
Standalone inference loader for ECG classifier checkpoints.

Supports:
- MoE checkpoints (experts.* + gate.* keys)
- MLP checkpoints (fc1/fc2/out keys)

Usage examples:
  python inference_loader.py --ckpt ./moe_classifier_medsiglip.pt --image ./ecg.png
  python inference_loader.py --ckpt ./mlp_classifier_medsiglip.pt --folder ./images --out ./preds.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


DEFAULT_MODEL_ID = "google/medsiglip-448"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


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

        dropout_values = tuple(dropout)
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


def get_device(device_arg: str) -> str:
    if device_arg == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device_arg == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return device_arg


def collect_images(image: str | None, images: list[str] | None, folder: str | None) -> list[str]:
    paths: list[str] = []
    if image:
        paths.append(image)
    if images:
        paths.extend(images)
    if folder:
        for name in sorted(os.listdir(folder)):
            p = os.path.join(folder, name)
            ext = os.path.splitext(p)[1].lower()
            if os.path.isfile(p) and ext in IMAGE_EXTS:
                paths.append(p)

    out: list[str] = []
    seen: set[str] = set()
    for p in paths:
        ap = str(Path(p).resolve())
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


def extract_features(output: Any) -> torch.Tensor:
    if isinstance(output, torch.Tensor):
        return output
    if hasattr(output, "pooler_output") and output.pooler_output is not None:
        return output.pooler_output
    if hasattr(output, "last_hidden_state") and output.last_hidden_state is not None:
        return output.last_hidden_state[:, 0, :]
    raise TypeError(f"Unexpected image feature output type: {type(output)}")


def build_classifier(ckpt: dict[str, Any]) -> tuple[nn.Module, str]:
    state_dict = ckpt.get("state_dict")
    if not isinstance(state_dict, dict) or not state_dict:
        raise RuntimeError("Checkpoint missing state_dict.")

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
            layer_index = int(key.split(".")[3])
            expert_linear_layers.append((layer_index, value))

        if len(expert_linear_layers) < 2:
            raise RuntimeError("Unable to infer expert architecture from checkpoint.")

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
        raise RuntimeError("Unsupported checkpoint format.")

    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model, model_type


@torch.no_grad()
def embed_images(
    embedder: AutoModel,
    processor: AutoImageProcessor,
    image_paths: list[str],
    batch_size: int,
) -> tuple[np.ndarray, list[str]]:
    embs: list[np.ndarray] = []
    kept: list[str] = []
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i : i + batch_size]
        batch_images = []
        batch_kept: list[str] = []
        for p in batch_paths:
            try:
                batch_images.append(Image.open(p).convert("RGB"))
                batch_kept.append(p)
            except Exception as exc:  # pragma: no cover
                print(f"[skip] {p}: {exc}")

        if not batch_images:
            continue

        inputs = processor(images=batch_images, return_tensors="pt").to(embedder.device)
        out = embedder.get_image_features(**inputs)
        feats = extract_features(out)

        embs.append(feats.detach().cpu().numpy().astype(np.float32))
        kept.extend(batch_kept)

    if not embs:
        return np.zeros((0, 0), dtype=np.float32), []
    return np.concatenate(embs, axis=0), kept


@torch.no_grad()
def predict(
    classifier: nn.Module,
    X_emb: np.ndarray,
    device: str,
) -> np.ndarray:
    xb = torch.from_numpy(X_emb).to(device)
    logits_output = classifier(xb)
    logits = logits_output[0] if isinstance(logits_output, tuple) else logits_output
    probs = torch.sigmoid(logits).detach().cpu().numpy()
    return probs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", type=str, required=True, help="Path to checkpoint .pt file")
    parser.add_argument("--model_id", type=str, default=DEFAULT_MODEL_ID, help="HF model id for embedder")
    parser.add_argument("--hf_token", type=str, default=None, help="HF token (or set HF_TOKEN env var)")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--threshold", type=float, default=None, help="Override checkpoint threshold")

    parser.add_argument("--image", type=str, default=None, help="Single image path")
    parser.add_argument("--images", nargs="*", default=None, help="Multiple image paths")
    parser.add_argument("--folder", type=str, default=None, help="Folder with images")
    parser.add_argument("--out", type=str, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    image_paths = collect_images(args.image, args.images, args.folder)
    if not image_paths:
        raise SystemExit("No images found. Use --image, --images, or --folder.")

    device = get_device(args.device)
    ckpt = torch.load(args.ckpt, map_location="cpu")
    if not isinstance(ckpt, dict):
        raise SystemExit("Checkpoint must be a dict.")

    classifier, model_type = build_classifier(ckpt)
    classifier.to(device)
    classifier.eval()

    embed_dim = int(ckpt["embed_dim"])
    num_classes = int(ckpt["num_classes"])
    threshold = float(args.threshold) if args.threshold is not None else float(ckpt.get("threshold", 0.5))
    classes = ckpt.get("classes")
    if not isinstance(classes, list) or len(classes) != num_classes:
        classes = [f"class_{i}" for i in range(num_classes)]

    token = args.hf_token or os.getenv("HF_TOKEN")
    embedder = AutoModel.from_pretrained(args.model_id, token=token)
    processor = AutoImageProcessor.from_pretrained(args.model_id, token=token)
    embedder.to(device)
    embedder.eval()

    X_emb, kept_paths = embed_images(embedder, processor, image_paths, args.batch_size)
    if X_emb.shape[0] == 0:
        raise SystemExit("No images could be processed.")
    if X_emb.shape[1] != embed_dim:
        raise SystemExit(
            f"Embedding dim mismatch: produced {X_emb.shape[1]} but checkpoint expects {embed_dim}."
        )

    probs = predict(classifier, X_emb, device=device)
    preds = (probs >= threshold).astype(int)

    summary = {
        "checkpoint": str(Path(args.ckpt).resolve()),
        "classifier_type": model_type,
        "model_id": args.model_id,
        "device": device,
        "num_images": len(kept_paths),
        "embed_dim": embed_dim,
        "num_classes": num_classes,
        "threshold": threshold,
    }
    if "num_experts" in ckpt:
        summary["num_experts"] = int(ckpt["num_experts"])

    results = []
    for image_path, row_prob, row_pred in zip(kept_paths, probs, preds):
        results.append(
            {
                "image_path": image_path,
                "scores_by_class": {label: float(score) for label, score in zip(classes, row_prob)},
                "predicted_labels": [label for label, y in zip(classes, row_pred) if int(y) == 1],
            }
        )

    payload = {"summary": summary, "results": results}
    print(json.dumps(summary, indent=2))
    print(json.dumps(results[:3], indent=2))

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Saved output to: {out_path}")


if __name__ == "__main__":
    main()
