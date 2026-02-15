"""
Mixture-of-Experts (MoE) classifier for multi-label ECG classification on MedSigLIP embeddings.

Inputs:
  ./dataset/ECG-Dataset/X_train_medsiglip.npy
  ./dataset/ECG-Dataset/Y_train.npy
  ./dataset/ECG-Dataset/X_val_medsiglip.npy
  ./dataset/ECG-Dataset/Y_val.npy
  ./dataset/ECG-Dataset/X_test_medsiglip.npy
  ./dataset/ECG-Dataset/Y_test.npy

Model:
  - Gate network outputs a distribution over experts (softmax)
  - Each expert is an MLP that outputs logits for each class
  - Final logits are a weighted sum of expert logits

Loss:
  - BCEWithLogitsLoss (multi-label)
  - + optional load-balancing loss to encourage gate usage diversity

Install:
  pip install numpy torch scikit-learn
"""

import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from sklearn.metrics import (
    hamming_loss,
    roc_auc_score,
    classification_report,
    multilabel_confusion_matrix,
)


# ---------------------- PATHS ----------------------
BASE = "./dataset/ECG-Dataset"
X_TRAIN_PATH = os.path.join(BASE, "X_train_medsiglip.npy")
Y_TRAIN_PATH = os.path.join(BASE, "Y_train.npy")
X_VAL_PATH   = os.path.join(BASE, "X_val_medsiglip.npy")
Y_VAL_PATH   = os.path.join(BASE, "Y_val.npy")
X_TEST_PATH  = os.path.join(BASE, "X_test_medsiglip.npy")
Y_TEST_PATH  = os.path.join(BASE, "Y_test.npy")

CLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]


# ---------------------- LOAD ----------------------
def load_xy(x_path, y_path):
    X = np.load(x_path).astype(np.float32)
    Y = np.load(y_path).astype(np.float32)
    if X.ndim != 2:
        raise ValueError(f"X must be 2D (N, D). Got {X.shape}")
    if Y.ndim != 2:
        raise ValueError(f"Y must be 2D (N, C). Got {Y.shape}")
    if X.shape[0] != Y.shape[0]:
        raise ValueError(f"X/Y mismatch: {X.shape[0]} vs {Y.shape[0]}")
    return X, Y

X_train, Y_train = load_xy(X_TRAIN_PATH, Y_TRAIN_PATH)
X_val,   Y_val   = load_xy(X_VAL_PATH,   Y_VAL_PATH)
X_test,  Y_test  = load_xy(X_TEST_PATH,  Y_TEST_PATH)

EMBED_DIM = X_train.shape[1]
NUM_CLASSES = Y_train.shape[1]
assert NUM_CLASSES == len(CLASSES), f"NUM_CLASSES={NUM_CLASSES}, CLASSES={len(CLASSES)}"

print("Shapes:")
print("  X_train:", X_train.shape, "Y_train:", Y_train.shape)
print("  X_val:  ", X_val.shape,   "Y_val:  ", Y_val.shape)
print("  X_test: ", X_test.shape,  "Y_test: ", Y_test.shape)


# ---------------------- DATALOADERS ----------------------
BATCH_SIZE = 256
NUM_WORKERS = 2

train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(Y_train))
val_ds   = TensorDataset(torch.from_numpy(X_val),   torch.from_numpy(Y_val))
test_ds  = TensorDataset(torch.from_numpy(X_test),  torch.from_numpy(Y_test))

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=NUM_WORKERS, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)


# ---------------------- MODEL ----------------------
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

        # Gate predicts weights over experts from embedding
        self.gate = nn.Sequential(
            nn.Linear(in_dim, gate_hidden),
            nn.ReLU(),
            nn.Linear(gate_hidden, num_experts),
        )

    def forward(self, x):
        # gate_logits: (B, E)
        gate_logits = self.gate(x) / self.temperature
        gate_w = torch.softmax(gate_logits, dim=-1)  # (B, E)

        # expert_logits: list of (B, C) -> stack -> (B, E, C)
        expert_logits = torch.stack([exp(x) for exp in self.experts], dim=1)

        # mix: (B, C)
        mixed_logits = torch.sum(expert_logits * gate_w.unsqueeze(-1), dim=1)

        return mixed_logits, gate_w, expert_logits


def load_balance_loss(gate_w: torch.Tensor):
    """
    Encourage balanced expert usage.
    gate_w: (B, E), soft weights.

    We want the mean gate weight per expert to be close to uniform.
    A simple penalty is squared error from 1/E.

    Returns scalar loss.
    """
    E = gate_w.size(1)
    usage = gate_w.mean(dim=0)  # (E,)
    target = torch.full_like(usage, 1.0 / E)
    return torch.mean((usage - target) ** 2)


device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

NUM_EXPERTS = 5
model = MoEClassifier(EMBED_DIM, NUM_CLASSES, num_experts=NUM_EXPERTS, gate_hidden=512, temperature=1.0).to(device)

criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)

LAMBDA_BALANCE = 0.10  # try 0.0 to disable, 0.01-0.1 typical


# ---------------------- TRAIN / EVAL ----------------------
def run_epoch(loader, train: bool):
    model.train() if train else model.eval()

    total_loss = 0.0
    total_main = 0.0
    total_bal = 0.0
    total_n = 0

    for xb, yb in loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            logits, gate_w, _ = model(xb)
            main_loss = criterion(logits, yb)

            bal_loss = load_balance_loss(gate_w) if LAMBDA_BALANCE > 0 else torch.tensor(0.0, device=device)
            loss = main_loss + LAMBDA_BALANCE * bal_loss

            if train:
                loss.backward()
                optimizer.step()

        bs = xb.size(0)
        total_loss += loss.item() * bs
        total_main += main_loss.item() * bs
        total_bal += bal_loss.item() * bs
        total_n += bs

    return (
        total_loss / max(total_n, 1),
        total_main / max(total_n, 1),
        total_bal / max(total_n, 1),
    )


@torch.no_grad()
def predict_probs(loader):
    model.eval()
    probs_list = []
    y_list = []
    gate_list = []
    for xb, yb in loader:
        xb = xb.to(device, non_blocking=True)
        logits, gate_w, _ = model(xb)
        probs = torch.sigmoid(logits).cpu().numpy()
        probs_list.append(probs)
        y_list.append(yb.cpu().numpy())
        gate_list.append(gate_w.cpu().numpy())
    return np.concatenate(probs_list, axis=0), np.concatenate(y_list, axis=0), np.concatenate(gate_list, axis=0)


# ---------------------- TRAINING LOOP ----------------------
EPOCHS = 100
best_val = float("inf")
best_state = None
patience = 10
bad = 0

for epoch in range(1, EPOCHS + 1):
    tr_loss, tr_main, tr_bal = run_epoch(train_loader, train=True)
    va_loss, va_main, va_bal = run_epoch(val_loader, train=False)

    print(f"Epoch {epoch:03d} | train_loss={tr_loss:.4f} main={tr_main:.4f} bal={tr_bal:.4f}")
    print(f"           | val_loss={va_loss:.4f}   main={va_main:.4f} bal={va_bal:.4f}")

    if LAMBDA_BALANCE > 0:
        print(f"           | val_loss={va_loss:.4f} (main={va_main:.4f}, bal={va_bal:.4f})")
    else:
        print(f"           | val_loss={va_loss:.4f}")

    if va_loss < best_val - 1e-6:
        best_val = va_loss
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        bad = 0
    else:
        bad += 1
        if bad >= patience:
            print(f"Early stopping at epoch {epoch:02d} (best val_loss={best_val:.4f})")
            break

if best_state is not None:
    model.load_state_dict(best_state)


# ---------------------- TEST METRICS ----------------------
y_prob, y_true, gate_w_all = predict_probs(test_loader)

threshold = 0.3
y_pred = (y_prob >= threshold).astype(int)
y_true = y_true.astype(int)

print("\nTest metrics:")
print("Hamming loss:", hamming_loss(y_true, y_pred))

try:
    micro_auc = roc_auc_score(y_true, y_prob, average="micro")
    macro_auc = roc_auc_score(y_true, y_prob, average="macro")
    print("ROC-AUC micro:", micro_auc)
    print("ROC-AUC macro:", macro_auc)
except ValueError as e:
    print("ROC-AUC could not be computed:", e)

cms = multilabel_confusion_matrix(y_true, y_pred)
print("\nPer-class confusion matrices at threshold =", threshold)
for i, cls in enumerate(CLASSES):
    tn, fp, fn, tp = cms[i].ravel()
    print(f"{cls:5s} | TP={tp:5d} FP={fp:5d} FN={fn:5d} TN={tn:5d}")

print("\nClassification report (per class):")
print(classification_report(y_true, y_pred, target_names=CLASSES, zero_division=0))

# Gate usage diagnostics
mean_gate = gate_w_all.mean(axis=0)
print("\nMean gate usage per expert (should not collapse to one expert):")
for i, val in enumerate(mean_gate):
    print(f"  expert_{i}: {val:.3f}")

# Save model
SAVE_PATH = os.path.join(BASE, "moe_classifier_medsiglip.pt")
torch.save(
    {
        "state_dict": model.state_dict(),
        "classes": CLASSES,
        "embed_dim": EMBED_DIM,
        "num_classes": NUM_CLASSES,
        "num_experts": NUM_EXPERTS,
        "threshold": threshold,
        "lambda_balance": LAMBDA_BALANCE,
    },
    SAVE_PATH,
)
print("\nSaved model to:", SAVE_PATH)
