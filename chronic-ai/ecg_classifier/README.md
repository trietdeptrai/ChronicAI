---
language:
- en
license: mit
library_name: pytorch
pipeline_tag: image-classification
tags:
- ecg
- medical-imaging
- multi-label-classification
- medsiglip
- mixture-of-experts
- mlp
model-index:
- name: ECG Image Classifier (MoE and MLP) on MedSigLIP Embeddings
  results:
  - task:
      type: image-classification
      name: Multi-label ECG image classification
    dataset:
      type: custom
      name: PTB-XL + supplementary ECG image dataset
    metrics:
    - type: hamming_loss
      value: 0.167
      name: Hamming loss (MoE)
    - type: roc_auc
      value: 0.891
      name: ROC-AUC micro (MoE)
    - type: roc_auc
      value: 0.879
      name: ROC-AUC macro (MoE)
---

# ECG Image Classifier (MoE and MLP) on MedSigLIP Embeddings

This repository provides two PyTorch ECG classifier checkpoints trained on top of frozen MedSigLIP image embeddings:

- `moe_classifier_medsiglip.pt`: Mixture-of-Experts (MoE) classifier
- `mlp_classifier_medsiglip.pt`: Dense feedforward (MLP) classifier

These checkpoints expect embeddings produced by:

- `google/medsiglip-448`

The repository contains only the classifier heads. MedSigLIP weights are not included and must be obtained separately under Google’s license.

---

## Motivation

This work was developed as part of the Google MedGemma Impact Challenge:  
https://www.kaggle.com/competitions/med-gemma-impact-challenge/overview

The goal is to build a lightweight, deployable ECG image classifier for chronic care screening, especially in low-resource clinical settings where ECG is often the most accessible diagnostic modality.

---

## Task and Data

We formulate a supervised multi-label image classification task on 12-lead ECGs with five diagnostic categories:

- NORM (normal)
- MI (myocardial infarction)
- STTC (ST-T changes)
- CD (conduction disturbances)
- HYP (hypertrophy)

Training data combines:

- PTB-XL, a large-scale dataset of raw 12-lead ECG waveforms in WFDB format with 16-bit precision [1]
- A supplementary ECG image dataset [2]

To enable image-based classification, raw PTB-XL waveforms are converted into realistic print-style ECG images using the open-source ECG image generator by Rahimi et al [3]. This yields approximately 21,000 synthetic ECG images, which are combined with 713 real ECG images from the supplementary dataset.

---

## Model and Training

ECG images are first encoded using MedSigLIP to obtain fixed-dimensional visual embeddings. Two lightweight classifiers are trained on top of these embeddings:

- A dense feedforward network (MLP)
- A Mixture-of-Experts (MoE) classifier

The dataset is split into 60 percent training, 20 percent validation, and 20 percent testing. Both models are optimized with Adam using a learning rate of 1e-4 and weight decay of 1e-5. The MoE model additionally uses a load-balancing regularization term with lambda set to 0.1.

For multi-label prediction, a uniform decision threshold of 0.3 is applied across all classes.

---

## Results

On the held-out test set, the MoE classifier consistently outperforms the MLP baseline across all metrics. It achieves:

- Lower Hamming loss: 0.167 vs 0.235
- Higher ROC-AUC:
  - Micro: 0.891 vs 0.827
  - Macro: 0.879 vs 0.808
- Higher F1 scores:
  - Micro: 0.70 vs 0.61
  - Macro: 0.67 vs 0.58

Per-class F1 improves across all five diagnostic categories, with the largest gains observed for myocardial infarction and hypertrophy. Confusion matrix analysis indicates that the MLP baseline tends to trade precision for recall, producing more false positives and a lower overall F1. For this reason, the MoE classifier is used in the final application.

---

## Practical Implications

Compared to using MedGemma alone, the MedSigLIP plus classifier pipeline provides more structured and reliable ECG predictions. In addition to discrete labels, the classifier outputs calibrated confidence scores. This supports threshold-based screening and triage, which is particularly useful in chronic care workflows and remote clinics where rapid ECG assessment can help prioritize referrals.

---

## How to Use

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Run inference

Single image with the MoE checkpoint:

```bash
python inference_loader.py \
  --ckpt ./moe_classifier_medsiglip.pt \
  --image ./sample_ecg.png \
  --out ./preds_moe.json
```

Batch inference on a folder with the MLP checkpoint:

```bash
python inference_loader.py \
  --ckpt ./mlp_classifier_medsiglip.pt \
  --folder ./images \
  --out ./preds_mlp.json
```

### 3) Optional arguments

- `--model_id` (default: `google/medsiglip-448`)
- `--device auto|cpu|cuda`
- `--batch_size 16`
- `--threshold 0.3` (overrides the checkpoint threshold)
- `--hf_token <token>` (or set `HF_TOKEN` as an environment variable)

### 4) Outputs

The inference script returns:

- `scores_by_class`: confidence scores for each diagnostic class
- `predicted_labels`: labels above the decision threshold
- `summary`: run metadata including checkpoint, model type, device, and embedding dimensions

---

## References

[1] PTB-XL dataset  
[2] Supplementary ECG image dataset used in this project  
[3] Rahimi et al., open-source ECG image generator
