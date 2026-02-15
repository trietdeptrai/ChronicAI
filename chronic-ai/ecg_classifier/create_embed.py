"""
End-to-end example:
1) Read classification_labels_3by4.csv (created from PTB-XL metadata + your generated images)
2) Build X_train/X_val/X_test as image paths
3) Build Y_train/Y_val/Y_test as labels (multi-label binary vector or single-label)
4) Pass images through google/medsiglip-448 to get embeddings
5) Return embeddings as the new X_* and labels as Y_*

Assumptions:
- Your CSV is at: ./dataset/ECG-Dataset/classification_labels_3by4.csv
- It contains columns: split, image_path, diagnostic_superclass_str
- diagnostic_superclass_str looks like: "NORM" or "MI,STTC" etc.
- Images are local files (NOT URLs). So we load with PIL directly.

Install needed deps:
  pip install pandas numpy pillow torch transformers tqdm
"""

import os
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

import torch
from transformers import AutoImageProcessor, AutoModel


CSV_PATH = "./dataset/ECG-Dataset/classification_labels_3by4.csv"

# Choose the label set you want to predict
# PTB-XL diagnostic superclasses usually include: NORM, MI, STTC, CD, HYP
CLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]

MODEL_ID = "google/medsiglip-448"


def parse_multilabel(diag_str: str, classes=CLASSES) -> np.ndarray:
    """
    Convert "MI,STTC" into a multi-hot vector of length len(classes).
    """
    if not isinstance(diag_str, str) or diag_str.strip() == "":
        return np.zeros(len(classes), dtype=np.int64)
    present = set([x.strip() for x in diag_str.split(",") if x.strip()])
    return np.array([1 if c in present else 0 for c in classes], dtype=np.int64)


def load_splits_from_csv(csv_path: str):
    df = pd.read_csv(csv_path)

    required = {"split", "image_path", "diagnostic_superclass_str"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Found: {list(df.columns)}")

    # Keep only rows whose image actually exists
    exists_mask = df["image_path"].apply(lambda p: isinstance(p, str) and os.path.exists(p))
    df = df[exists_mask].copy()

    # Build X paths
    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]
    test_df = df[df["split"] == "test"]

    X_train = train_df["image_path"].tolist()
    X_val = val_df["image_path"].tolist()
    X_test = test_df["image_path"].tolist()

    # Build Y (multi-label)
    Y_train = np.stack([parse_multilabel(s) for s in train_df["diagnostic_superclass_str"].tolist()], axis=0)
    Y_val = np.stack([parse_multilabel(s) for s in val_df["diagnostic_superclass_str"].tolist()], axis=0)
    Y_test = np.stack([parse_multilabel(s) for s in test_df["diagnostic_superclass_str"].tolist()], axis=0)

    return X_train, Y_train, X_val, Y_val, X_test, Y_test


def embed_images_with_medsiglip(X_image_paths, y, batch_size=64):
    """
    Returns:
      X_emb: (N, D) float32 numpy array
      Y_out: (N, ...) numpy array (same order as embeddings)
    """
    model = AutoModel.from_pretrained(MODEL_ID, device_map="auto")
    image_processor = AutoImageProcessor.from_pretrained(MODEL_ID)

    embeddings = []
    labels = []

    num_images = len(X_image_paths)
    for i in tqdm(range(0, num_images, batch_size), desc="Embedding"):
        batch_paths = X_image_paths[i:i + batch_size]
        batch_labels = y[i:i + batch_size]

        X_images = []
        y_labels = []

        for image_path, row_labels in zip(batch_paths, batch_labels):
            try:
                img = Image.open(image_path).convert("RGB")
                X_images.append(img)
                y_labels.append(row_labels)
            except Exception as e:
                print(f"[skip] {image_path}: {e}")

        if not X_images:
            continue

        inputs = image_processor(images=X_images, return_tensors="pt").to(model.device)

        with torch.no_grad():
            out = model.get_image_features(**inputs)
        
        # out can be a Tensor OR a ModelOutput object depending on transformers/model version
        if isinstance(out, torch.Tensor):
            feats = out
        elif hasattr(out, "pooler_output") and out.pooler_output is not None:
            feats = out.pooler_output
        elif hasattr(out, "last_hidden_state") and out.last_hidden_state is not None:
            # fallback: take CLS token
            feats = out.last_hidden_state[:, 0, :]
        else:
            raise TypeError(f"Unexpected output type from get_image_features: {type(out)}")
        
        embeddings.append(feats.cpu().numpy())

        labels.append(np.stack(y_labels, axis=0))

    X_emb = np.concatenate(embeddings, axis=0).astype(np.float32)
    Y_out = np.concatenate(labels, axis=0)

    return X_emb, Y_out


if __name__ == "__main__":
    # 1) Load paths and labels
    X_train_paths, Y_train, X_val_paths, Y_val, X_test_paths, Y_test = load_splits_from_csv(CSV_PATH)

    print("Loaded splits:")
    print("  train:", len(X_train_paths), Y_train.shape)
    print("  val:  ", len(X_val_paths), Y_val.shape)
    print("  test: ", len(X_test_paths), Y_test.shape)

    # 2) Convert images -> embeddings (new X)
    # Adjust batch_size based on GPU/VRAM. If you get OOM, reduce.
    X_train, Y_train = embed_images_with_medsiglip(X_train_paths, Y_train, batch_size=64)
    X_val, Y_val = embed_images_with_medsiglip(X_val_paths, Y_val, batch_size=64)
    X_test, Y_test = embed_images_with_medsiglip(X_test_paths, Y_test, batch_size=64)

    print("\nEmbeddings ready:")
    print("  X_train:", X_train.shape, "Y_train:", Y_train.shape)
    print("  X_val:  ", X_val.shape, "Y_val:  ", Y_val.shape)
    print("  X_test: ", X_test.shape, "Y_test:", Y_test.shape)

    # Optional: save
    np.save("./dataset/ECG-Dataset/X_train_medsiglip.npy", X_train)
    np.save("./dataset/ECG-Dataset/Y_train.npy", Y_train)
    np.save("./dataset/ECG-Dataset/X_val_medsiglip.npy", X_val)
    np.save("./dataset/ECG-Dataset/Y_val.npy", Y_val)
    np.save("./dataset/ECG-Dataset/X_test_medsiglip.npy", X_test)
    np.save("./dataset/ECG-Dataset/Y_test.npy", Y_test)
