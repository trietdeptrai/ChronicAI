# ECG Classifier

This folder contains the ECG image classification pipeline used by ChronicAI.

It uses:
- MedSigLIP (`google/medsiglip-448`) to convert ECG images into embeddings
- a classifier head on top of embeddings:
  - MoE (`moe_classifier_medsiglip.pt`) - recommended
  - MLP (`mlp_classifier_medsiglip.pt`)

## 1. Quick Start (Run Inference)

From `chronic-ai/ecg_classifier/`:

```bash
pip install -r requirements.txt
```

Single image (MoE):

```bash
python inference_loader.py --ckpt ./embed_data/moe_classifier_medsiglip.pt --image ./sample_ecg.png --out ./preds_moe.json
```

Batch folder:

```bash
python inference_loader.py --ckpt ./embed_data/moe_classifier_medsiglip.pt --folder ./images --out ./preds_moe.json
```

Important options:
- `--model_id google/medsiglip-448`
- `--device auto|cpu|cuda`
- `--batch_size 16`
- `--threshold 0.3`
- `--hf_token <token>` (or set `HF_TOKEN`)

## 2. Expected Data and Artifacts

Default training paths are under:

```text
./dataset/ECG-Dataset/
  X_train_medsiglip.npy
  Y_train.npy
  X_val_medsiglip.npy
  Y_val.npy
  X_test_medsiglip.npy
  Y_test.npy
```

Existing checkpoints in this repo:

```text
./embed_data/moe_classifier_medsiglip.pt
./embed_data/mlp_classifier_medsiglip.pt
```

## 3. Re-train Deterministically

Use fixed seed + deterministic mode:

```bash
python train_classifier.py --seed 42 --deterministic
```

Useful flags:
- `--base ./dataset/ECG-Dataset`
- `--epochs 100`
- `--patience 10`
- `--threshold 0.3`
- `--num_experts 5`
- `--save_path ./embed_data/moe_classifier_medsiglip.pt`

Training now saves reproducibility metadata:
- inside checkpoint key `run_metadata`
- sidecar JSON: `<checkpoint>.metadata.json`

Metadata includes:
- runtime versions
- seed and deterministic flag
- dataset shapes
- hyperparameters

## 4. Full Pipeline (If You Need to Regenerate Data)

Typical order:

1. Generate detection/image dataset:
```bash
python make_dataset.py
```
2. Build classification labels:
```bash
python make_classification_label.py
```
3. Build MedSigLIP embeddings:
```bash
python create_embed.py
```
4. Train classifier:
```bash
python train_classifier.py --seed 42 --deterministic
```

## 5. Output Format

Inference output JSON includes:
- `scores_by_class`
- `predicted_labels`
- `summary`

Diagnostic classes:
- `NORM`
- `MI`
- `STTC`
- `CD`
- `HYP`

## 6. Known Performance (MoE)

- Hamming loss: `0.167`
- ROC-AUC micro: `0.891`
- ROC-AUC macro: `0.879`

## 7. Troubleshooting

- `FileNotFoundError` on `.npy` files:
  - verify `--base` path
  - ensure embedding generation completed

- Hugging Face/auth errors:
  - set `HF_TOKEN`
  - ensure access to `google/medsiglip-448`

- CUDA OOM:
  - reduce `--batch_size`
  - run with `--device cpu` if needed

- Non-reproducible metrics:
  - use `--seed` + `--deterministic`
  - keep same dataset split and same package versions
