# ChronicAI

Vietnam is facing a rapidly growing chronic disease burden, but the information needed to manage long-term care is still scattered across disconnected places: hospital systems, lab portals, PDF reports, imaging files, prescriptions, and appointment logs. That fragmentation makes it hard to see a patient’s story as one continuous timeline, especially when decisions need to be made quickly.

This is happening while clinicians are under intensifying pressure. In Vietnam, outpatient departments in major hospitals may have to examine roughly 150 to 200 patients per day, and some specialties go even higher, which compresses consultation time and pushes more of the “record reconstruction” work onto already overloaded doctors. In parallel, research in Vietnam continues to show meaningful levels of psychological strain in the health workforce, including measurable stress and burnout signals.

ChronicAI is built to close that continuity gap. It centralizes scattered records into a longitudinal patient view and adds conversational AI support, so clinicians spend less time hunting for context and more time making treatment decisions with the full history in front of them.

## Key Features

- Context-driven medical chat for doctors and patients, powered by MedGemma for clearer communication and better between-visit support.
- Automated record ingestion: upload medical documents/PDFs and convert them into structured clinical data.
- Longitudinal clinical summarization and risk-oriented workflow support to improve triage and follow-up decisions.
- Multimodal image support for CT, MRI, X-ray, and ECG, with AI-generated preliminary interpretations for clinician review.
- ECG-focused screening pipeline using MedSigLIP + a lightweight Mixture-of-Experts classifier for efficient heart-pattern triage.
- Privacy-first architecture with support for local/on-premise deployment patterns, while this repository's default setup uses Vertex AI.

The sections below cover what you need to run the app locally: required accounts, environment setup, database initialization, and verification checks.

## 1. What You Need

### 1.1 External Accounts and Access (Required)

Before running the app, make sure you have:

- A Supabase account and project with:
  - project URL
  - anon key
  - service role key
- A Google Cloud project with Vertex AI enabled and a deployed endpoint that can serve chat completions.
- Local Google Cloud CLI (`gcloud`) installed and authenticated on your machine.
- Access to the selected LLM provider path (default in this repo is Vertex).
<<<<<<< Updated upstream
- Hugging Face token (`HF_TOKEN`) with access to `google/medsiglip-448` if you use ECG embedding/inference flows.

Without these, the app will start but core AI/ECG features will fail.
=======
- Hugging Face token (`HF_TOKEN`) with access to `google/medsiglip-448` for ECG embedding/inference flows.

Without these, the app will start but core AI/ECG features will fail. `HF_TOKEN` is a hard requirement for ECG features.
>>>>>>> Stashed changes

### 1.2 Local Runtime Versions

- Node.js `20.19.0` (see `.nvmrc`)
- npm `10.x`
- Python `3.11.9+` (3.11.x, see `.python-version`)

<<<<<<< Updated upstream
=======
Version management tips:
- Node.js: run `nvm use` from `chronic-ai/` to load the version in `.nvmrc`.
- Python: use `pyenv` to install/pin `3.11.9` to avoid dependency/runtime mismatch issues.
  - example:
```bash
pyenv install 3.11.9
pyenv local 3.11.9
python --version
```

>>>>>>> Stashed changes
## 2. Project Structure

```text
chronic-ai/
  frontend/        # Next.js app
  api/             # FastAPI + LangGraph workflows
  ecg_classifier/  # ECG model pipeline
  migrations/      # SQL migrations
  supabase/        # Supabase config/migrations
```

## 3. Quick Start (Recommended)

<<<<<<< Updated upstream
From `chronic-ai/`:
=======
From repository root (`ChronicAI/`), move into the app directory first:

```bash
cd chronic-ai
```

Then run bootstrap:
>>>>>>> Stashed changes

- Windows (PowerShell):
```powershell
.\scripts\bootstrap.ps1
```

- macOS/Linux:
```bash
bash ./scripts/bootstrap.sh
```

This will:
- create `.venv`
- install backend dependencies
- install ECG classifier dependencies
- install frontend dependencies with `npm ci`
- create `api/.env` from `api/.env.example` if missing
- create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` if missing

## 4. Configure Environment

Follow these steps in order.

1. Create backend env file:
- bootstrap auto-creates `api/.env` from `api/.env.example` when missing
- fill required values (Supabase, model/provider settings)

2. Prepare Google Cloud auth on your machine (required by backend runtime):
- install Google Cloud CLI (`gcloud`)
- run:
```bash
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>
gcloud auth application-default login
```
- confirm token command works:
```bash
gcloud auth print-access-token
```

3. Fill required Supabase variables in `api/.env`:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

Where to find these in Supabase:
- open your Supabase project dashboard
- go to `Project Settings` -> `API`
- copy:
  - `Project URL` -> `SUPABASE_URL`
  - `anon public` key -> `SUPABASE_ANON_KEY`
  - `service_role` key -> `SUPABASE_SERVICE_ROLE_KEY`

4. Configure LLM provider in `api/.env`:
- set `LLM_PROVIDER=vertex` (default path in this repo)
- set:
  - `VERTEX_AI_HOST`
  - `VERTEX_AI_PROJECT_ID`
  - `VERTEX_AI_LOCATION`
  - `VERTEX_AI_ENDPOINT_ID`
  - `VERTEX_AI_MODEL`
- set model routing:
  - `MEDICAL_MODEL`
  - `VERIFICATION_MODEL`

How to fill Vertex values exactly:
- `VERTEX_AI_PROJECT_ID`:
  - your Google Cloud project ID (same value used in `gcloud config set project ...`)
- `VERTEX_AI_LOCATION`:
  - endpoint region, for example `us-central1` or `europe-west4`
- `VERTEX_AI_ENDPOINT_ID`:
  - Vertex Endpoint ID from `Vertex AI` -> `Online prediction` -> `Endpoints` -> select endpoint -> `Endpoint ID`
- `VERTEX_AI_HOST`:
  - endpoint host root only (no path)
  - expected format:
    - dedicated endpoint host: `https://<endpoint-host>.prediction.vertexai.goog`
    - or regional API host: `https://<location>-aiplatform.googleapis.com`
- `VERTEX_AI_MODEL`:
<<<<<<< Updated upstream
  - set to the model name your endpoint serves (the identifier expected by your endpoint deployment)
  - if one model is deployed, use that same model identifier here
- `MEDICAL_MODEL` and `VERIFICATION_MODEL`:
  - set both to the same model identifier unless you intentionally run different models
  - recommended starting point: use the same value as `VERTEX_AI_MODEL`

How to decide which model to deploy on Vertex:
- this app sends OpenAI-style `chat/completions` requests to your endpoint
- deploy one chat-capable model behind your endpoint, then use that model's exact identifier in:
  - `VERTEX_AI_MODEL`
  - `MEDICAL_MODEL`
  - `VERIFICATION_MODEL`
- if you are unsure which identifier to use:
  - open Vertex endpoint details
  - find the currently deployed model entry
  - copy the model name/identifier shown for that deployment
- do not leave these fields empty; backend health checks require them

5. Set ECG/MedSigLIP access in `api/.env`:
- `HF_TOKEN` (required for private/auth-gated access)
=======
  - this project standard is MedGemma 27B on Vertex AI
  - set to `google/medgemma-27b-it` (the model identifier expected by your endpoint deployment)
- `MEDICAL_MODEL` and `VERIFICATION_MODEL`:
  - set both to the same value as `VERTEX_AI_MODEL`
  - use `google/medgemma-27b-it` for both

How to decide which model to deploy on Vertex:
- this app sends OpenAI-style `chat/completions` requests to your endpoint
- deploy MedGemma 27B behind your endpoint, then use its identifier in:
  - `VERTEX_AI_MODEL`
  - `MEDICAL_MODEL`
  - `VERIFICATION_MODEL`
- expected identifier in this repo:
  - `google/medgemma-27b-it`
- if you need to confirm what is currently deployed on your endpoint:
  - open Vertex endpoint details
  - verify the deployed model entry is MedGemma 27B
- do not leave these fields empty; backend health checks require them

5. Set ECG/MedSigLIP access in `api/.env`:
- `HF_TOKEN` (hard requirement for ECG features; required for private/auth-gated model access)
>>>>>>> Stashed changes
- optionally keep defaults unless you changed artifacts:
  - `ECG_MEDSIGLIP_MODEL_ID=google/medsiglip-448`
  - `ECG_CLASSIFIER_CHECKPOINT_PATH=ecg_classifier/embed_data/moe_classifier_medsiglip.pt`

6. Create frontend env file `frontend/.env.local`:
- bootstrap auto-creates this file when missing

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

7. Verify checkpoint artifact exists:
- confirm `ecg_classifier/embed_data/moe_classifier_medsiglip.pt` is present
- if missing, retrain/regenerate from `ecg_classifier/README.md`

8. Quick required-value checklist before starting services:
- `api/.env` has non-empty values for:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `LLM_PROVIDER=vertex`
  - `VERTEX_AI_HOST`
  - `VERTEX_AI_PROJECT_ID`
  - `VERTEX_AI_LOCATION`
  - `VERTEX_AI_ENDPOINT_ID`
  - `VERTEX_AI_MODEL`
  - `MEDICAL_MODEL`
  - `VERIFICATION_MODEL`
- `frontend/.env.local` has:
  - `NEXT_PUBLIC_API_URL`

## 5. Setup Database (Supabase)

Run these SQL files in your Supabase SQL editor, in this order:

1. `chronic-ai/setup_db.sql`
2. `chronic-ai/setup_vector_search.sql`
3. `chronic-ai/seed_demo_data.sql` (optional but useful for testing/demo)

Important:
<<<<<<< Updated upstream
=======
- enable the `vector` extension (`pgvector`) on your Supabase project before running `chronic-ai/setup_vector_search.sql`
>>>>>>> Stashed changes
- run them on the same Supabase project whose credentials you put in `api/.env`
- if migrations are skipped/out of order, API queries and RAG features can fail

## 6. Run the App

Start backend:

- Windows:
```bash
cd api
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- macOS/Linux:
```bash
cd api
../.venv/bin/python -m uvicorn app.main:app --reload
```

Start frontend (new terminal):

```bash
cd frontend
npm run dev
```

Open:
- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

## 7. Verify Everything Works

1. API health:
- open `http://localhost:8000/docs`
- ensure endpoints are listed and callable

2. Environment sanity checks:
- backend logs should not show missing env var errors
- Vertex calls should not return auth/permission errors
- Supabase calls should not return key/schema errors
- ECG endpoint path should resolve configured checkpoint file

Recommended quick checks from terminal:
```bash
gcloud auth print-access-token
```
```bash
cd api
..\.venv\Scripts\python.exe -c "from app.config import settings; print(settings.llm_provider, settings.vertex_ai_project_id, settings.vertex_ai_location, settings.vertex_ai_endpoint_id)"
```

3. SSE streaming:
- test `POST /chat/doctor/v2/stream`
- test `POST /chat/patient/v2/stream`
- confirm response streams multiple `stage` updates

4. Safety behavior:
- doctor flow can return `hitl_required`
- patient flow escalates high-risk/self-harm scenarios

5. RAG path:
- ensure Supabase credentials are valid
- verify patient context retrieval succeeds

## 8. Common Commands

Frontend:

```bash
cd frontend
npm run dev
npm run build
npm run lint
```

Backend:

```bash
cd api
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
pytest
```

ECG classifier (deterministic training):

```bash
cd ecg_classifier
..\.venv\Scripts\python.exe train_classifier.py --seed 42 --deterministic
```

## 9. Troubleshooting

- Backend cannot connect to Supabase:
  - recheck `api/.env` values
  - verify project URL/key permissions

- Frontend cannot call API:
  - verify `frontend/.env.local`
  - ensure backend is running on port `8000`

- Install issues:
  - rerun bootstrap script (it now stops on failed dependency installs)
  - confirm Node/Python versions match section 1

- Slow first AI response:
  - model/provider warm-up can take time on first request

## 10. Additional Docs

- ECG module details: `ecg_classifier/README.md`
- Design/engineering notes remain under `docs/` and other project markdown files.
