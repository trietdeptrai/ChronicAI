# ChronicAI: ECG Classifier Vertex AI Migration Guide

We have migrated the ECG classification pipeline from local PyTorch inference (which required ~2.5GB of dependencies) to an API-based architecture using **Vertex AI Custom Prediction**. This guide explains the new architecture and provide step-by-step instructions for deployment and backend configuration.

---

## 🏗 New Architecture

1.  **Backend** sends a base64-encoded ECG image to a **Vertex AI Custom Endpoint**.
2.  **Vertex AI Endpoint** runs the full pipeline: MedSigLIP image embedding → MoE Classifier scores.
3.  **Backend** receives the scores and passes them to **MedGemma** (also via Vertex AI) for final clinical analysis.

> [!NOTE]
> This migration allows the web backend to remain extremely lightweight while retaining specialized ECG classification capabilities.

---

## ✅ Work Completed

### 1. Serving Container
A standalone serving environment has been created in `chronic-ai/ecg_classifier/serving/`:
- `serve.py`: FastAPI app wrapping MedSigLIP + MoE classifier.
- `Dockerfile`: Production-ready container based on `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`.
- `requirements.txt`: Minimal dependencies for the inference container.

### 2. Backend Refactor (Lightweight API)
- **`app/services/ecg_classifier_service.py`**: Completely rewritten. It no longer imports `torch` or `transformers`. It now makes authenticated HTTP calls to the Vertex AI endpoint.
- **`app/config.py` & `.env.example`**: Updated to include `ECG_CLASSIFIER_ENDPOINT_URL` and `ECG_CLASSIFIER_ENDPOINT_TIMEOUT`.
- **`app/services/llm.py`**: Updated calling site to be async/await compatible.

---

## 🚀 Deployment Instructions

### Prerequisites
- Google Cloud project with Vertex AI API enabled.
- `gcloud` CLI installed and authenticated.
- Docker installed locally.

### Step 1: Set Variables
```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export REPO_NAME=chronicai
export IMAGE_NAME=ecg-classifier
export IMAGE_TAG=latest
export IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}
```

### Step 2: Create Artifact Registry Repository (Once)
```bash
gcloud artifacts repositories create ${REPO_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --project=${PROJECT_ID}
```

### Step 3: Build & Push Serving Container
```bash
cd chronic-ai/ecg_classifier/serving

# Configure Docker for Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
docker build -t ${IMAGE_URI} .
docker push ${IMAGE_URI}
```

### Step 4: Upload Model Artifacts to GCS
Vertex AI requires the `.pt` checkpoint to be stored in a GCS bucket.
```bash
# Create a GCS bucket for model artifacts
gsutil mb -l ${REGION} gs://${PROJECT_ID}-ecg-models/

# Upload the checkpoint
gsutil cp ../embed_data/moe_classifier_medsiglip.pt \
    gs://${PROJECT_ID}-ecg-models/ecg-classifier-v1/
```

### Step 5: Import Model into Vertex AI
1. Go to **Vertex AI → Model Registry → Import**.
2. Select **Import an existing custom container**.
3. Fill in the following:

| Field | Value |
| :--- | :--- |
| **Container image** | `${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ecg-classifier:latest` |
| **Model artifact location** | `gs://${PROJECT_ID}-ecg-models/ecg-classifier-v1/` |
| **Inference route** | `/predict` |
| **Health route** | `/health` |
| **Port** | `8080` |

> [!TIP]
> Add `HF_TOKEN` as an environment variable in the container settings if your MedSigLIP model ID requires HuggingFace authentication.

### Step 6: Deploy to an Endpoint
1. Go to **Vertex AI → Online prediction → Endpoints → Create**.
2. Deploy the imported model.
3. Select a machine type with a GPU (e.g., `n1-standard-4` with 1x NVIDIA T4).
4. After deployment, copy the **Endpoint URL**.

---

## ⚙️ Backend Configuration

Update your backend `.env` file with the new endpoint URL:

```bash
ECG_CLASSIFIER_ENDPOINT_URL=https://<endpoint-id>.prediction.vertexai.goog/v1/projects/<project>/locations/<region>/endpoints/<endpoint-id>:predict
ECG_CLASSIFIER_ENDPOINT_TIMEOUT=60
```

---

## 🧪 Verification

### Local Container Testing
You can test the container locally before pushing:
```bash
cd chronic-ai/ecg_classifier/serving
docker build -t ecg-classifier .
docker run -p 8080:8080 \
    -e CHECKPOINT_PATH=/models/moe_classifier_medsiglip.pt \
    -v $(pwd)/../embed_data:/models \
    ecg-classifier

# Test Health
curl http://localhost:8080/health

# Test Prediction
curl -X POST http://localhost:8080/predict \
    -H "Content-Type: application/json" \
    -d '{"image_base64": "<base64_data>"}'
```

### Backend Verification
Run the FastAPI backend and upload an ECG image. Monitor the logs for `[ecg-classifier] predict complete (remote)`.
If the endpoint is not configured, the system will automatically fall back to MedGemma-only analysis (graceful degradation).
