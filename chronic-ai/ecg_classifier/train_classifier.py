"""
Train ECG classifier heads on MedSigLIP embeddings.

Supports:
  - MoE classifier
  - MLP classifier
"""

import argparse
import json
import os
import platform
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, hamming_loss, multilabel_confusion_matrix, roc_auc_score
from torch.utils.data import DataLoader, TensorDataset


CLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]


def parse_args():
    parser = argparse.ArgumentParser(description="Train deterministic MoE/MLP classifier on MedSigLIP ECG embeddings.")
    parser.add_argument("--base", type=str, default="./dataset/ECG-Dataset", help="Dataset/artifact base directory.")
    parser.add_argument("--model_type", type=str, default="moe", choices=["moe", "mlp"], help="Classifier type.")
    parser.add_argument("--seed", type=int, default=42, help="Global random seed.")
    parser.add_argument("--deterministic", action="store_true", help="Enable deterministic PyTorch operations.")
    parser.add_argument("--batch_size", type=int, default=256, help="Batch size.")
    parser.add_argument("--num_workers", type=int, default=2, help="DataLoader workers.")
    parser.add_argument("--epochs", type=int, default=100, help="Maximum training epochs.")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience.")
    parser.add_argument("--threshold", type=float, default=0.3, help="Inference threshold for test metrics.")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate.")
    parser.add_argument("--weight_decay", type=float, default=1e-5, help="Weight decay.")

    parser.add_argument("--num_experts", type=int, default=5, help="Number of MoE experts.")
    parser.add_argument("--gate_hidden", type=int, default=512, help="MoE gate hidden size.")
    parser.add_argument("--temperature", type=float, default=1.0, help="MoE gate softmax temperature.")
    parser.add_argument("--lambda_balance", type=float, default=0.10, help="MoE load-balancing regularization.")

    parser.add_argument("--mlp_hidden_1", type=int, default=1024, help="MLP hidden layer 1 size.")
    parser.add_argument("--mlp_hidden_2", type=int, default=512, help="MLP hidden layer 2 size.")
    parser.add_argument("--mlp_dropout", type=float, default=0.15, help="MLP dropout.")

    parser.add_argument("--save_path", type=str, default=None, help="Optional output checkpoint path.")
    return parser.parse_args()


def seed_everything(seed: int, deterministic: bool):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    else:
        torch.backends.cudnn.benchmark = True


def load_xy(x_path, y_path):
    x = np.load(x_path).astype(np.float32)
    y = np.load(y_path).astype(np.float32)
    if x.ndim != 2:
        raise ValueError(f"X must be 2D (N, D). Got {x.shape}")
    if y.ndim != 2:
        raise ValueError(f"Y must be 2D (N, C). Got {y.shape}")
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"X/Y mismatch: {x.shape[0]} vs {y.shape[0]}")
    return x, y


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
        layers.append(nn.Linear(prev, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class MoEClassifier(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, num_experts: int = 4, gate_hidden: int = 256, temperature: float = 1.0):
        super().__init__()
        self.temperature = temperature
        self.experts = nn.ModuleList([ExpertMLP(in_dim, out_dim) for _ in range(num_experts)])
        self.gate = nn.Sequential(
            nn.Linear(in_dim, gate_hidden),
            nn.ReLU(),
            nn.Linear(gate_hidden, num_experts),
        )

    def forward(self, x):
        gate_logits = self.gate(x) / self.temperature
        gate_w = torch.softmax(gate_logits, dim=-1)
        expert_logits = torch.stack([exp(x) for exp in self.experts], dim=1)
        mixed_logits = torch.sum(expert_logits * gate_w.unsqueeze(-1), dim=1)
        return mixed_logits, gate_w


class MLPClassifier(nn.Module):
    # Keep layer names fc1/fc2/out for compatibility with inference_loader.py
    def __init__(self, in_dim: int, out_dim: int, hidden_1: int = 1024, hidden_2: int = 512, dropout: float = 0.15):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_1)
        self.fc2 = nn.Linear(hidden_1, hidden_2)
        self.out = nn.Linear(hidden_2, out_dim)
        self.act = nn.ReLU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        x = self.drop(self.act(self.fc1(x)))
        x = self.drop(self.act(self.fc2(x)))
        return self.out(x)


def load_balance_loss(gate_w: torch.Tensor):
    e = gate_w.size(1)
    usage = gate_w.mean(dim=0)
    target = torch.full_like(usage, 1.0 / e)
    return torch.mean((usage - target) ** 2)


def run_epoch(loader, train: bool, model, optimizer, criterion, device, model_type: str, lambda_balance: float):
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
            if model_type == "moe":
                logits, gate_w = model(xb)
                main_loss = criterion(logits, yb)
                bal_loss = load_balance_loss(gate_w) if lambda_balance > 0 else torch.tensor(0.0, device=device)
                loss = main_loss + lambda_balance * bal_loss
            else:
                logits = model(xb)
                main_loss = criterion(logits, yb)
                bal_loss = torch.tensor(0.0, device=device)
                loss = main_loss

            if train:
                loss.backward()
                optimizer.step()

        bs = xb.size(0)
        total_loss += loss.item() * bs
        total_main += main_loss.item() * bs
        total_bal += bal_loss.item() * bs
        total_n += bs

    return total_loss / max(total_n, 1), total_main / max(total_n, 1), total_bal / max(total_n, 1)


@torch.no_grad()
def predict_probs(loader, model, device, model_type: str):
    model.eval()
    probs_list = []
    y_list = []
    gate_list = []
    for xb, yb in loader:
        xb = xb.to(device, non_blocking=True)
        if model_type == "moe":
            logits, gate_w = model(xb)
            gate_list.append(gate_w.cpu().numpy())
        else:
            logits = model(xb)
        probs = torch.sigmoid(logits).cpu().numpy()
        probs_list.append(probs)
        y_list.append(yb.cpu().numpy())

    gates = np.concatenate(gate_list, axis=0) if gate_list else None
    return np.concatenate(probs_list, axis=0), np.concatenate(y_list, axis=0), gates


def main():
    args = parse_args()
    seed_everything(args.seed, args.deterministic)

    base = args.base
    x_train_path = os.path.join(base, "X_train_medsiglip.npy")
    y_train_path = os.path.join(base, "Y_train.npy")
    x_val_path = os.path.join(base, "X_val_medsiglip.npy")
    y_val_path = os.path.join(base, "Y_val.npy")
    x_test_path = os.path.join(base, "X_test_medsiglip.npy")
    y_test_path = os.path.join(base, "Y_test.npy")

    x_train, y_train = load_xy(x_train_path, y_train_path)
    x_val, y_val = load_xy(x_val_path, y_val_path)
    x_test, y_test = load_xy(x_test_path, y_test_path)

    embed_dim = x_train.shape[1]
    num_classes = y_train.shape[1]
    assert num_classes == len(CLASSES), f"NUM_CLASSES={num_classes}, CLASSES={len(CLASSES)}"

    print("Shapes:")
    print("  X_train:", x_train.shape, "Y_train:", y_train.shape)
    print("  X_val:  ", x_val.shape, "Y_val:  ", y_val.shape)
    print("  X_test: ", x_test.shape, "Y_test: ", y_test.shape)

    train_ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(x_val), torch.from_numpy(y_val))
    test_ds = TensorDataset(torch.from_numpy(x_test), torch.from_numpy(y_test))

    data_loader_generator = torch.Generator()
    data_loader_generator.manual_seed(args.seed)

    pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=pin_memory,
        generator=data_loader_generator,
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=pin_memory)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=pin_memory)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Device:", device)

    if args.model_type == "moe":
        model = MoEClassifier(
            embed_dim,
            num_classes,
            num_experts=args.num_experts,
            gate_hidden=args.gate_hidden,
            temperature=args.temperature,
        ).to(device)
    else:
        model = MLPClassifier(
            embed_dim,
            num_classes,
            hidden_1=args.mlp_hidden_1,
            hidden_2=args.mlp_hidden_2,
            dropout=args.mlp_dropout,
        ).to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    epochs = args.epochs
    best_val = float("inf")
    best_state = None
    bad = 0

    for epoch in range(1, epochs + 1):
        tr_loss, tr_main, tr_bal = run_epoch(
            train_loader, True, model, optimizer, criterion, device, args.model_type, args.lambda_balance
        )
        va_loss, va_main, va_bal = run_epoch(
            val_loader, False, model, optimizer, criterion, device, args.model_type, args.lambda_balance
        )

        print(f"Epoch {epoch:03d} | train_loss={tr_loss:.4f} main={tr_main:.4f} bal={tr_bal:.4f}")
        print(f"           | val_loss={va_loss:.4f}   main={va_main:.4f} bal={va_bal:.4f}")

        if va_loss < best_val - 1e-6:
            best_val = va_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
            if bad >= args.patience:
                print(f"Early stopping at epoch {epoch:02d} (best val_loss={best_val:.4f})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    y_prob, y_true, gate_w_all = predict_probs(test_loader, model, device, args.model_type)
    threshold = args.threshold
    y_pred = (y_prob >= threshold).astype(int)
    y_true = y_true.astype(int)

    print("\nTest metrics:")
    print("Hamming loss:", hamming_loss(y_true, y_pred))

    try:
        micro_auc = roc_auc_score(y_true, y_prob, average="micro")
        macro_auc = roc_auc_score(y_true, y_prob, average="macro")
        print("ROC-AUC micro:", micro_auc)
        print("ROC-AUC macro:", macro_auc)
    except ValueError as exc:
        print("ROC-AUC could not be computed:", exc)

    cms = multilabel_confusion_matrix(y_true, y_pred)
    print("\nPer-class confusion matrices at threshold =", threshold)
    for i, cls in enumerate(CLASSES):
        tn, fp, fn, tp = cms[i].ravel()
        print(f"{cls:5s} | TP={tp:5d} FP={fp:5d} FN={fn:5d} TN={tn:5d}")

    print("\nClassification report (per class):")
    print(classification_report(y_true, y_pred, target_names=CLASSES, zero_division=0))

    if args.model_type == "moe" and gate_w_all is not None:
        mean_gate = gate_w_all.mean(axis=0)
        print("\nMean gate usage per expert (should not collapse to one expert):")
        for i, val in enumerate(mean_gate):
            print(f"  expert_{i}: {val:.3f}")

    default_name = "moe_classifier_medsiglip.pt" if args.model_type == "moe" else "mlp_classifier_medsiglip.pt"
    save_path = args.save_path or os.path.join(base, default_name)
    Path(os.path.dirname(save_path) or ".").mkdir(parents=True, exist_ok=True)

    run_metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "device": device,
        "seed": args.seed,
        "deterministic": args.deterministic,
        "paths": {
            "base": base,
            "x_train": x_train_path,
            "y_train": y_train_path,
            "x_val": x_val_path,
            "y_val": y_val_path,
            "x_test": x_test_path,
            "y_test": y_test_path,
        },
        "dataset_shapes": {
            "x_train": list(x_train.shape),
            "y_train": list(y_train.shape),
            "x_val": list(x_val.shape),
            "y_val": list(y_val.shape),
            "x_test": list(x_test.shape),
            "y_test": list(y_test.shape),
        },
        "hyperparameters": {
            "model_type": args.model_type,
            "batch_size": args.batch_size,
            "num_workers": args.num_workers,
            "epochs": epochs,
            "patience": args.patience,
            "learning_rate": args.lr,
            "weight_decay": args.weight_decay,
            "threshold": threshold,
            "num_experts": args.num_experts,
            "gate_hidden": args.gate_hidden,
            "temperature": args.temperature,
            "lambda_balance": args.lambda_balance,
            "mlp_hidden_1": args.mlp_hidden_1,
            "mlp_hidden_2": args.mlp_hidden_2,
            "mlp_dropout": args.mlp_dropout,
        },
    }

    checkpoint = {
        "state_dict": model.state_dict(),
        "classes": CLASSES,
        "embed_dim": embed_dim,
        "num_classes": num_classes,
        "threshold": threshold,
        "model_type": args.model_type,
        "run_metadata": run_metadata,
    }
    if args.model_type == "moe":
        checkpoint["num_experts"] = args.num_experts
        checkpoint["lambda_balance"] = args.lambda_balance

    torch.save(checkpoint, save_path)
    print("\nSaved model to:", save_path)

    metadata_path = os.path.splitext(save_path)[0] + ".metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(run_metadata, f, indent=2)
    print("Saved run metadata to:", metadata_path)


if __name__ == "__main__":
    main()
