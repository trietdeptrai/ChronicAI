# Technical Writeup Plan: Is the technical solution clearly feasible?

Based on your project's implementation (ChronicAI), here is a structured guide on what to write to effectively address the criteria and showcase the feasibility of your technical solution. 

## 1. Model Fine-Tuning & Custom Architecture
Instead of just saying you used MedGemma, showcase the engineering effort around your specialized models:
- **ECG Classifier (Mixture-of-Experts)**: Highlight your custom PyTorch multi-label classifier built on MedSigLIP embeddings. Explain the architecture (Soft MoE where a gating network mixes expert logits) and why it's optimal for classifying complex ECG patterns (NORM, MI, STTC, CD, HYP).
- **Model roles in the actual workflow**: Describe how ChronicAI splits responsibilities across *what the code actually calls*: MedGemma powers (1) doctor/patient medical reasoning, (2) symptom triage classification, and (3) uploaded record analysis (text + optional image). A configurable verification model (defaulting to MedGemma in `settings.verification_model`) runs lightweight `verification_service.verify_input()` and `check_response_safety()` for input clarity + post-response safety review. RAG embeddings are generated via a configurable provider (`settings.embedding_provider`, local deterministic `hash` by default) and stored in `pgvector` for retrieval.

## 2. Model Performance Analysis
Move beyond generic accuracy and discuss metrics that matter in healthcare:
- **Classifier Metrics**: Point out that your model evaluation goes deep into multi-label effectiveness using Hamming Loss, ROC-AUC (micro/macro), and per-class Confusion Matrices. Mention the load-balancing loss implemented to ensure expert usage diversity in the MoE architecture.
- **MedGemma + verifier runtime behavior**: Ground this in the deployed workflow: the primary path is a remote OpenAI-compatible Vertex endpoint (`LLM_PROVIDER=vertex`) configured to serve your MedGemma deployment (e.g., MedGemma 27B). Ollama (`LLM_PROVIDER=ollama`) exists as an optional local fallback for development/offline use. Highlight the resilience work that makes it usable in a clinical UI—retry/backoff + circuit breakers around LLM calls, plus a separate short-token verification pass for safety and clarity.
- **Structured output quality**: Point out that uploaded record analysis (`analyze_uploaded_record`) enforces a strict JSON schema, and doctor answers are post-processed into consistent sections (assessment / recommendations / warnings) via `output_formatter.py` so clinicians can skim and act.
- **RAG Latency/Accuracy**: Mention the speed and retrieval precision of mapping patient queries against pgvector embeddings.

## 2.5 Prompt Engineering (the concrete prompts you actually ship)
Avoid hand-wavy “we did prompt engineering” claims—show 4–6 *real* prompt snippets and explain why each exists (determinism, safety, structure, latency).

**Why this demonstrates effective MedGemma usage (not just “we called an LLM”)**:
- **Right tool for the right subtask**: MedGemma is used where its clinical language + reasoning strengths matter (doctor/patient responses, Vietnamese clinical note structure, and image-aware reasoning), while a lightweight verifier pass focuses on *clarity + safety* with strict JSON outputs.
- **Prompt modularity mirrors clinical workflow**: instead of forcing one prompt to do everything, the system composes multiple short, purpose-built prompts (verify → extract → retrieve context → reason → safety review → format), which yields more stable behavior and easier debugging in production.
- **Model outputs are made actionable for clinicians**: formatting constraints (sections, bullets, short paragraphs) plus a post-formatter (`output_formatter.py`) turn MedGemma’s raw generation into skimmable notes (assessment/recommendations/warnings) aligned with real clinical reading patterns.

### A) Doctor reasoning: query-type-aware system prompts (LangGraph)
In `api/app/services/doctor_graph.py`, `_build_system_prompt(query_type)` returns different system prompts depending on whether the doctor’s question is general, patient-specific, aggregate, or image-analysis. All variants share strict safety rules (no hallucinations/placeholders, refuse non-medical, Vietnamese-only).

**Shared safety rules (excerpt)**:
```text
QUY TẮC AN TOÀN:
1. CHỈ cung cấp thông tin dựa trên dữ liệu được cung cấp
2. KHÔNG BAO GIỜ bịa đặt thông tin bệnh nhân, kết quả xét nghiệm, hoặc tiền sử bệnh
3. KHÔNG sử dụng placeholder như [Insert...], [TODO], [N/A]
4. Nếu thiếu thông tin quan trọng, nói rõ "Không đủ dữ liệu"
6. TỪ CHỐI mọi yêu cầu ngoài y khoa (ví dụ: làm thơ, kể chuyện, viết code, giải trí)
8. Trả lời hoàn toàn bằng tiếng Việt
```

**Patient-specific doctor prompt (excerpt)**:
```text
Bạn là trợ lý AI y khoa hỗ trợ bác sĩ quản lý bệnh nhân.

Bác sĩ đang hỏi về bệnh nhân cụ thể. Hãy cung cấp đánh giá có cấu trúc.
CHỈ bao gồm các phần liên quan đến câu hỏi (không cần tất cả):

## Đánh giá
## Phân tích
## Đề xuất
## Cảnh báo

YÊU CẦU ĐỊNH DẠNG (BẮT BUỘC):
- Mỗi đoạn tối đa 2-3 câu, không viết thành một khối văn bản dài
```

### B) “Small, strict” JSON-only prompts for determinism (verifier + triage + extraction)
These prompts are intentionally short and schema-constrained so the app can parse outputs reliably and branch the graph.

**Input verification (clarity/ambiguity) in `api/app/services/verification_service.py` (excerpt)**:
```text
You are a medical query analyzer...
Output a JSON object with these fields:
{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["..."],
  "suggested_rewrites": ["..."],
  "needs_clarification": true/false
}
Output ONLY the JSON, no other text.
```

**Response safety review (post-check) in `api/app/services/verification_service.py` (excerpt)**:
```text
You are a medical response safety reviewer...
Output ONLY the JSON, no other text.
```

**Patient urgency triage in `api/app/services/patient_graph.py` (excerpt)**:
```text
You are a medical triage assistant...
IMPORTANT: When in doubt, err on the side of caution and classify higher.
Output ONLY valid JSON: {"urgency": "level", "reason": "brief reason", "confidence": 0.0-1.0}
```

**Doctor patient-name extraction in `api/app/services/doctor_graph.py` (excerpt)**:
```text
Extract patient names from the query.
Output ONLY a valid JSON array of names: ["Name1", "Name2"] or [] if no patients mentioned.
IMPORTANT: If the query is a general medical question NOT about a specific patient, return [].
```

### C) Patient-facing tone + refusal policy (patient chat)
In `api/app/services/patient_graph.py`, the patient system prompt optimizes for empathy + safety: Vietnamese-only, simple language, no prescribing/dosages, no definitive diagnoses, and explicit refusal for non-medical requests.

**Patient chat system prompt (excerpt)**:
```text
You are a supportive medical AI assistant for patients.
Respond entirely in Vietnamese

CRITICAL GUIDELINES:
- Do NOT prescribe medication or dosages
- Do NOT give definitive diagnoses
- Refuse non-medical requests (poems, stories, entertainment, coding, weather, finance)
- NEVER make up information - only use what's in the patient context
```

### D) Upload analysis: strict JSON-only output
In `api/app/services/llm.py`, uploaded record analysis uses a JSON-only system prompt to produce machine-ingestible summaries for downstream UX.

```text
You are a clinical decision-support assistant for doctors.
You must return valid JSON only (no markdown or extra commentary).
```

## 3. User-Facing Application Stack
Show the judges that this is a robust, production-ready application and not just a notebook script.
- **Frontend**: Next.js 16 App Router, React 19, Tailwind CSS 4, and Radix UI. Emphasize that there are role-specific dashboards (Doctors vs. Patients) built with accessibility and real clinical workflows in mind.
- **Backend**: Python FastAPI delivering high-concurrency API performance.
- **Orchestration**: Highlight the use of **LangGraph** to power stateful multi-step agent pipelines:
  - **Asynchronous Streaming (SSE)**: Built on top of LangGraph `.astream()`, execution progress through the graph (e.g., `translate_input`, `verify_input`, `extract_patients`, `resolve_patients`, `get_context`, `medical_reasoning`, `safety_check`) is pushed to the frontend in real-time via Server-Sent Events, so the UI stays responsive during long model calls.
  - **Stateful Memory & Human-in-the-Loop (HITL)**: Uses `MemorySaver` checkpointing keyed by `thread_id` to persist graph state across requests. In the Doctor graph, execution pauses via LangGraph `interrupt()` and resumes via `/chat/doctor/v2/resume` with a structured payload (clarification / patient selection / approval decision).
  - **Dynamic Branching & Triage**: In the Patient graph, conditional edges evaluate the output of a `symptom_triage` node. If self-harm keywords or emergency conditions are detected, the graph automatically reroutes the pipeline to a dedicated `escalation_handler` instead of standard medical reasoning.
- **Database**: PostgreSQL with `pgvector` (via Supabase) for RAG embeddings and record retrieval, plus Supabase Storage for storing uploaded PDFs/images linked to patient records.

## 4. Patient Safety, Security & Practical Utility
This is a core pillar for healthcare products—stress these points carefully:
- **Human-In-The-Loop (HITL) in the Doctor workflow**: In `/chat/doctor/v2/stream`, `doctor_graph.py` uses LangGraph `interrupt()` to pause at *actual* decision points in this app: (1) `verify_input_node` asks for clarification when `verification_service.verify_input()` reports low-confidence / needs-clarification, (2) `resolve_patients_node` requests confirmation when fuzzy matching returns multiple plausible patients, and (3) `safety_check_node` requires explicit approval when `check_response_safety()` flags risk factors. The UI resumes the exact thread via `/chat/doctor/v2/resume` using `thread_id` (checkpointed with `MemorySaver`).
- **Safety triage in the Patient workflow**: `patient_graph.py` runs `symptom_triage_node` *before* any medical reasoning. It hard-overrides self-harm intent with deterministic keyword matching, and otherwise uses MedGemma to classify `urgency_level` (emergency/high/medium/low). Emergency/high cases route to `escalation_handler_node` (short-circuit to “seek urgent care”) instead of generating diagnostic-style advice.
- **Data handling (only what the current workflow does)**: When `LLM_PROVIDER=vertex`, prompts (and any attached record images) are sent to your configured Vertex endpoint; the app reduces exposure by retrieving only top-k RAG chunks (`get_patient_context(..., max_chunks=3)` for patient chat and `max_chunks=5` for doctor chat) and by attaching record images only when requested/relevant (and capped in `doctor_graph.py`). Uploaded PDFs/images are stored in Supabase Storage; chat transcripts persist to `chat_conversations` / `chat_messages` only when a `conversation_id` is provided.
- **Practical utility (burnout reduction in concrete terms)**: Doctors upload PDFs/images via `/upload/document`; PDFs run PaddleOCR (`ocr.py`) to extract text, and `ingest_document()` chunks + embeds the content for `pgvector` RAG. During chat, the Doctor graph automatically extracts patient mentions, fetches the most relevant record context (and optional record images), and MedGemma returns a structured Vietnamese note (assessment / recommendations / warnings) via `output_formatter.py`, with safety/triage decisions logged through `safety_audit`.

## 5. Deployment Challenges & Future Plan
Judges appreciate transparency about technical roadblocks and architectural foresight.
- **Challenges Overcome (what’s already implemented)**:
  - *Keeping latency predictable (and the UI “alive”)*: Long-running model calls are streamed as SSE stage updates (LangGraph node-by-node progress), so clinicians/patients see exactly what step is running instead of a frozen UI.
  - *Graceful degradation under model/API failures*: Circuit breakers + retries in `resilience.py` (OPEN/HALF_OPEN/CLOSED), plus defensive response patterns (uncertainty disclaimers + explicit “I don’t know” fallbacks) when verifier/reasoner calls are unavailable or low-confidence.
  - *Avoiding repeated-cost spikes for common queries*: An in-memory TTL + LRU `ResponseCache` (`cache.py`) reduces repeated LLM calls for similar/normalized prompts (and can be invalidated per patient context).
  - *27B model inference constraints on local hardware*: We could not reliably run the full MedGemma 27B locally (memory/latency constraints), so production inference is deployed as our own Vertex AI endpoint instead of calling a generic third-party LLM API service. This keeps the model deployment inside our cloud boundary and lets us control access via GCP IAM/OAuth (no static API keys in the app).
  - *OCR in real deployments (dependency pain + performance)*: PaddleOCR + PDF OCR requires heavyweight runtime deps (`paddlepaddle`, `paddleocr`, `pdf2image`, and Poppler’s `pdfinfo`). `ocr.py` treats OCR as an optional path with explicit `OCRDependencyError` messaging, Poppler path auto-detection (`POPPLER_PATH` / `OCR_POPPLER_PATH`), and CPU-bound OCR moved to a thread pool to keep the FastAPI event loop responsive.

- **Deployment Architecture (how to describe it succinctly to judges)**:
  - *Config-driven model routing*: `LLM_PROVIDER` toggles between a remote OpenAI-compatible Vertex endpoint (production) and Ollama (local/offline development), making it clear the app is not locked to a single runtime.
  - *“Self-hosted” managed inference posture*: Using a Vertex AI endpoint means we deploy and operate the model within our own GCP project (and can scope access via IAM), rather than sending sensitive prompts to an external API provider we don’t control.
  - *Stateless API with resumable conversations*: SSE endpoints stream work, while LangGraph checkpointing (`thread_id`) enables “pause/resume” HITL without holding a request open forever—important for horizontal scaling.
  - *Externalized state & storage*: Postgres + `pgvector` (RAG retrieval) and object storage for PDFs/images (so API containers don’t need a shared filesystem).

- **Future Plan (roadmap that signals production maturity)**:
  - *Background job pipeline for ingestion/OCR*: Move document OCR + chunking/embedding into async workers with progress events, so uploads don’t block request threads and large PDFs don’t degrade interactive chat latency.
  - *Observability & SLOs*: Add per-node latency metrics (SSE stage timing), error budgets, and dashboards for circuit breaker state, retry rates, and verifier “needs-clarification” frequency.
    Today, we get user-facing progress from SSE stage updates and rely on application logs for debugging, but we don’t yet have end-to-end traces/metrics that can follow a single ingestion or chat request through upload → OCR → chunking/embedding → verification → generation (and into downstream dependencies like the DB and LLM provider). The future architecture adds distributed tracing plus SLOs/error budgets so on-call can quickly answer “where did the time go?” and “what failed?” during real traffic spikes—surfacing signals like circuit-breaker trips, retry exhaustion, and how often the verifier requests clarification.
  - *Persistent safety/audit trail*: Extend `safety_audit` from in-memory logging to durable storage (DB table + retention policy) for clinical QA, incident review, and model governance.
    Today, `safety_audit` keeps a bounded in-memory buffer and emits a summarized line to standard logs; entries can be lost on restart and are not queryable by patient, time window, or model/prompt version. The future architecture persists safety-critical events in a queryable store with sensible retention (and links back to conversations/records), so QA and compliance teams can reconstruct complete timelines for incident review, post-deployment monitoring, and audits.
  - *Security hardening*: Centralized secrets management, fine-grained RBAC for doctor vs. patient access, encryption/rotation policies, and structured PII minimization (e.g., redact before logging/analytics).
    Today, secrets are primarily configured via environment variables and several API flows trust client-provided identifiers (e.g., `doctor_id` / `patient_id`) without a fully enforced identity + authorization layer; and we don’t yet have systematic PII redaction across logs/telemetry. The future architecture adds centralized secrets, strict RBAC across clinicians/patients/admins, encryption + key-rotation policies, and structured PII minimization so observability/debugging can’t become a data-leak path.
  - *Model governance & updates*: Prompt/version pinning, automated regression evals on a curated clinical test set, and canary rollouts for new reasoning/verifier models before full deployment.
