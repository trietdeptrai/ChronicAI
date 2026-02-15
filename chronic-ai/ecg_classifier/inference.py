"""
Run inference for the MoE classifier trained in train_classifier.py.

Pipeline:
  image(s) -> google/medsiglip-448 image embeddings -> MoEClassifier -> sigmoid -> predictions

Usage examples:
  # Single image
  python run_inference.py --image ./some_ecg.png

  # Multiple images
  python run_inference.py --images ./a.png ./b.png ./c.png

  # Folder of images (png/jpg/jpeg/webp/bmp)
  python run_inference.py --folder ./ecg_images --out ./preds.json

Dependencies:
  pip install torch transformers pillow numpy tqdm
"""

import os
import json
import argparse
from typing import List, Dict, Any

import numpy as np
from PIL import Image
from tqdm import tqdm

import torch
import torch.nn as nn
from transformers import AutoImageProcessor, AutoModel


# ---------------------- DEFAULTS ----------------------
MODEL_ID = "google/medsiglip-448"

DEFAULT_BASE = "./dataset/ECG-Dataset"
DEFAULT_CKPT = os.path.join(DEFAULT_BASE, "moe_classifier_medsiglip.pt")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ---------------------- MODEL (same architecture as training) ----------------------
class ExpertMLP(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, hidden=(1028, 512, 256), dropout=(0.15, 0.15, 0.10)):
        super().__init__()
        layers = []
        prev = in_dim
        for h, p in zip(hidden, dropout):
            layers.append(nn.Linear(prev, h))
            layers.append(nn.LayerNorm(h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(p))
            prev = h
        layers.append(nn.Linear(prev, out_dim))  # logits
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class MoEClassifier(nn.Module):
    """
    Soft MoE: compute all expert logits and mix with gate weights.
    """
    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        num_experts: int = 4,
        gate_hidden: int = 256,
        temperature: float = 1.0,
    ):
        super().__init__()
        self.num_experts = num_experts
        self.temperature = temperature

        self.experts = nn.ModuleList([ExpertMLP(in_dim, out_dim) for _ in range(num_experts)])

        self.gate = nn.Sequential(
            nn.Linear(in_dim, gate_hidden),
            nn.ReLU(),
            nn.Linear(gate_hidden, num_experts),
        )

    def forward(self, x):
        gate_logits = self.gate(x) / self.temperature
        gate_w = torch.softmax(gate_logits, dim=-1)  # (B, E)
        expert_logits = torch.stack([exp(x) for exp in self.experts], dim=1)  # (B, E, C)
        mixed_logits = torch.sum(expert_logits * gate_w.unsqueeze(-1), dim=1)  # (B, C)
        return mixed_logits, gate_w, expert_logits


# ---------------------- UTILS ----------------------
def get_device(device_arg: str) -> str:
    if device_arg != "auto":
        return device_arg
    return "cuda" if torch.cuda.is_available() else "cpu"


def collect_images(image: str, images: List[str], folder: str) -> List[str]:
    paths = []
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

    # de-dup while preserving order
    seen = set()
    out = []
    for p in paths:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


def safe_open_rgb(path: str):
    img = Image.open(path).convert("RGB")
    return img


@torch.no_grad()
def embed_images_medsiglip(
    model: AutoModel,
    processor: AutoImageProcessor,
    image_paths: List[str],
    batch_size: int,
) -> np.ndarray:
    """
    Returns numpy float32 embeddings of shape (N, D)
    """
    embs = []

    for i in tqdm(range(0, len(image_paths), batch_size), desc="Embedding"):
        batch_paths = image_paths[i:i + batch_size]
        batch_imgs = []
        kept_paths = []

        for p in batch_paths:
            try:
                batch_imgs.append(safe_open_rgb(p))
                kept_paths.append(p)
            except Exception as e:
                print(f"[skip] {p}: {e}")

        if not batch_imgs:
            continue

        inputs = processor(images=batch_imgs, return_tensors="pt").to(model.device)

        out = model.get_image_features(**inputs)

        # transformers/model version differences:
        if isinstance(out, torch.Tensor):
            feats = out
        elif hasattr(out, "pooler_output") and out.pooler_output is not None:
            feats = out.pooler_output
        elif hasattr(out, "last_hidden_state") and out.last_hidden_state is not None:
            feats = out.last_hidden_state[:, 0, :]
        else:
            raise TypeError(f"Unexpected output type from get_image_features: {type(out)}")

        embs.append(feats.detach().cpu().numpy())

    if not embs:
        return np.zeros((0, 0), dtype=np.float32)

    return np.concatenate(embs, axis=0).astype(np.float32)


def load_classifier(ckpt_path: str, device: str):
    ckpt = torch.load(ckpt_path, map_location="cpu")

    classes = ckpt.get("classes", None)
    embed_dim = int(ckpt["embed_dim"])
    num_classes = int(ckpt["num_classes"])
    num_experts = int(ckpt.get("num_experts", 4))
    threshold = float(ckpt.get("threshold", 0.5))

    # Match training hyperparams used in your file
    # (train_classifier.py used gate_hidden=512, temperature=1.0)
    model = MoEClassifier(
        in_dim=embed_dim,
        out_dim=num_classes,
        num_experts=num_experts,
        gate_hidden=512,
        temperature=1.0,
    )

    model.load_state_dict(ckpt["state_dict"], strict=True)
    model.to(device)
    model.eval()

    return model, classes, threshold, embed_dim, num_classes, num_experts


@torch.no_grad()
def predict(
    clf: MoEClassifier,
    X_emb: np.ndarray,
    device: str,
    threshold: float,
) -> Dict[str, Any]:
    xb = torch.from_numpy(X_emb).to(device)
    logits, gate_w, _ = clf(xb)
    probs = torch.sigmoid(logits).cpu().numpy()
    gate = gate_w.cpu().numpy()

    y_pred = (probs >= threshold).astype(int)
    return {"probs": probs, "pred": y_pred, "gate_w": gate}


def format_results(
    image_paths: List[str],
    probs: np.ndarray,
    pred: np.ndarray,
    classes: List[str],
) -> List[Dict[str, Any]]:
    if classes is None:
        classes = [f"class_{i}" for i in range(probs.shape[1])]

    results = []
    for p, pr, pd in zip(image_paths, probs, pred):
        results.append(
            {
                "image_path": p,
                "probs": {c: float(v) for c, v in zip(classes, pr)},
                "pred": {c: int(v) for c, v in zip(classes, pd)},
                "pred_labels": [c for c, v in zip(classes, pd) if int(v) == 1],
            }
        )
    return results


# ---------------------- MAIN ----------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=str, default=DEFAULT_CKPT, help="Path to moe_classifier_medsiglip.pt")
    ap.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"], help="Device")
    ap.add_argument("--batch_size", type=int, default=32, help="Batch size for MedSigLIP embedding")

    ap.add_argument("--image", type=str, default=None, help="Single image path")
    ap.add_argument("--images", nargs="*", default=None, help="Multiple image paths")
    ap.add_argument("--folder", type=str, default=None, help="Folder containing images")

    ap.add_argument("--out", type=str, default=None, help="Optional output JSON path")
    ap.add_argument("--threshold", type=float, default=None, help="Override threshold (default: from checkpoint)")

    args = ap.parse_args()

    device = get_device(args.device)

    image_paths = collect_images(args.image, args.images, args.folder)
    if not image_paths:
        raise SystemExit("No images provided. Use --image, --images, or --folder.")

    if not os.path.exists(args.ckpt):
        raise SystemExit(f"Checkpoint not found: {args.ckpt}")

    # Load classifier
    clf, classes, ckpt_threshold, embed_dim, num_classes, num_experts = load_classifier(args.ckpt, device)
    threshold = args.threshold if args.threshold is not None else ckpt_threshold

    # Load MedSigLIP embedder
    # Note: using device_map can be convenient, but we keep it explicit for predictable behavior
    embedder = AutoModel.from_pretrained(MODEL_ID)
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)

    embedder.to(device)
    embedder.eval()

    # Embed
    X_emb = embed_images_medsiglip(embedder, processor, image_paths, batch_size=args.batch_size)
    if X_emb.ndim != 2 or X_emb.shape[0] != len(image_paths):
        # This can happen if some images failed to load and got skipped.
        # For simplicity, fail loudly so you notice.
        raise SystemExit(
            f"Embedding mismatch. Got embeddings shape {X_emb.shape} for {len(image_paths)} images.\n"
            f"Check logs for [skip] lines or reduce batch_size."
        )

    if X_emb.shape[1] != embed_dim:
        raise SystemExit(
            f"Embedding dim mismatch: embedder produced {X_emb.shape[1]}, "
            f"but classifier expects {embed_dim}. Check MODEL_ID / checkpoint."
        )

    # Predict
    out = predict(clf, X_emb, device=device, threshold=threshold)

    results = format_results(image_paths, out["probs"], out["pred"], classes)

    summary = {
        "ckpt": os.path.abspath(args.ckpt),
        "model_id": MODEL_ID,
        "device": device,
        "num_images": len(image_paths),
        "embed_dim": int(embed_dim),
        "num_classes": int(num_classes),
        "num_experts": int(num_experts),
        "threshold": float(threshold),
    }

    payload = {"summary": summary, "results": results}

    # Print a compact preview
    print(json.dumps(summary, indent=2))
    print("\nPreview (first 3):")
    print(json.dumps(results[:3], indent=2))

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nSaved predictions to: {args.out}")


if __name__ == "__main__":
    main()
