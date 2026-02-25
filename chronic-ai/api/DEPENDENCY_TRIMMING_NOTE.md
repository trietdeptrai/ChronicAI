# Dependency Trimming for Online Deployment

**Date:** 2026-02-24  
**Author:** Automated cleanup  
**Purpose:** Reduce deployment image size for online hosting by removing heavy ML/AI packages not required for the core web application.

---

## Summary

`chronic-ai/api/requirements.txt` was trimmed from **146 → 95 packages**, removing **51 packages** that are only used for local ML inference. This reduces the deployment footprint by an estimated **4+ GB**.

## Removed Packages

The following categories of packages were removed:

### PyTorch & Related (~2+ GB)
| Package | Reason |
|---------|--------|
| `torch==2.8.0` | Deep learning framework — used by `transformers_client.py` (VinAI translation) and `ecg_classifier_service.py` |
| `accelerate==1.10.1` | PyTorch training/inference accelerator |
| `safetensors==0.7.0` | Model weight file format |
| `sympy==1.14.0` | Symbolic math — PyTorch transitive dependency |
| `networkx==3.6.1` | Graph library — PyTorch transitive dependency |
| `mpmath==1.3.0` | Arbitrary-precision math — PyTorch transitive dependency |
| `opt-einsum==3.3.0` | Tensor contraction — PyTorch transitive dependency |
| `filelock==3.20.3` | File locking — model download dependency |
| `fsspec==2026.2.0` | Filesystem abstraction — HuggingFace dependency |

### HuggingFace Transformers (~hundreds of MB)
| Package | Reason |
|---------|--------|
| `transformers==4.57.6` | NLP/vision model library — used by VinAI translation & ECG classifier |
| `huggingface_hub==0.36.2` | Model hub client |
| `hf-xet==1.2.0` | HuggingFace storage backend |
| `tokenizers==0.22.2` | Fast tokenizer library |
| `sentencepiece==0.2.1` | Text tokenization for VinAI models |
| `xxhash==3.6.0` | Hash library — tokenizers dependency |

### PaddlePaddle & PaddleOCR (~1+ GB)
| Package | Reason |
|---------|--------|
| `paddlepaddle==3.2.2` | Deep learning framework for OCR |
| `paddleocr==3.3.0` | OCR engine — used by `ocr.py` |
| `paddlex==3.3.13` | PaddlePaddle model toolkit |
| `opencv-contrib-python==4.10.0.84` | Computer vision — PaddleOCR dependency |
| `pyclipper==1.4.0` | Polygon clipping — PaddleOCR dependency |
| `shapely==2.1.2` | Geometry — PaddleOCR dependency |
| `python-bidi==0.6.7` | Bidirectional text — PaddleOCR dependency |
| `pyparsing==3.3.2` | Parsing — OpenCV dependency |

### PDF Processing
| Package | Reason |
|---------|--------|
| `pdf2image==1.17.0` | PDF to image conversion — used by `ocr.py` |
| `pypdfium2==5.3.0` | PDF rendering |
| `imagesize==1.4.1` | Image dimension reading |

### Other Removed Packages
| Package | Reason |
|---------|--------|
| `modelscope==1.34.0` | Model hub — not imported anywhere in API code |
| `aistudio-sdk==0.3.8` | AI Studio SDK — PaddlePaddle dependency |
| `bce-python-sdk==0.9.60` | Baidu Cloud SDK — PaddlePaddle dependency |
| `cffi==2.0.0` | C Foreign Function Interface — cryptography dependency |
| `chardet==5.2.0` | Character encoding detection — not directly used |
| `cryptography==46.0.4` | Cryptographic library — not directly used |
| `future==1.0.0` | Python 2/3 compatibility — PaddlePaddle dependency |
| `mmh3==5.2.0` | MurmurHash — not directly used |
| `pandas==3.0.0` | Data manipulation — not imported in API code |
| `prettytable==3.17.0` | Table formatting — PaddlePaddle dependency |
| `protobuf==6.33.5` | Protocol Buffers — PaddlePaddle dependency |
| `psutil==7.2.2` | System monitoring — not directly used |
| `py-cpuinfo==9.0.0` | CPU info — PaddlePaddle dependency |
| `pycparser==3.0` | C parser — cffi dependency |
| `pycryptodome==3.23.0` | Cryptography — not directly used |
| `pyiceberg==0.10.0` | Data lakehouse — not used |
| `pyroaring==1.0.3` | Roaring bitmaps — not used |
| `ruamel.yaml==0.19.1` | YAML parser — PaddlePaddle dependency |
| `shellingham==1.5.4` | Shell detection — typer dependency |
| `strictyaml==1.7.3` | Strict YAML — PaddlePaddle dependency |
| `typer-slim==0.21.1` | CLI framework — PaddlePaddle dependency |

---

## Affected Features

The following services use **lazy imports** and will **gracefully degrade** (the API will still start and serve all other endpoints):

| Service | File | Feature | Status |
|---------|------|---------|--------|
| VinAI Translation | `transformers_client.py` | Vietnamese ↔ English translation | ⚠️ Will fail at runtime if called |
| ECG Classifier | `ecg_classifier_service.py` | ECG image classification via MedSigLIP | ⚠️ Will fail at runtime if called |
| OCR | `ocr.py` | Medical document text extraction | ⚠️ Will fail at runtime if called |

> **Note:** All three services use deferred/lazy imports with try-except guards, so the API server will boot normally. Only calling these specific endpoints will produce an error.

---

## How to Restore

If you need ML features back for local development or a GPU-enabled deployment, the original full requirements are preserved in git history. You can also install the ML extras on top:

```bash
# Restore PyTorch + Transformers (for VinAI translation & ECG classifier)
pip install torch transformers accelerate safetensors sentencepiece huggingface_hub tokenizers

# Restore PaddleOCR (for OCR service)
pip install paddlepaddle paddleocr pdf2image opencv-contrib-python
```
