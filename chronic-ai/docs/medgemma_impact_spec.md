# MedGemma Impact Challenge - ChronicAI Spec

Last updated: 2026-02-06

## 1. Competition Criteria (Needs Verification)
I could not access the Kaggle competition page from this environment. The items below are
summarized from secondary sources and must be confirmed against the official rules.

- Use at least one HAI-DEF model (including MedGemma).
- Build a working demo application with real-world healthcare utility.
- Emphasis on privacy-first and local/edge-friendly deployment.
- Judging criteria likely include: problem importance, real-world impact, technical
  feasibility, execution/communication quality, and effective model usage.
- Submission package likely includes: short demo video, technical overview (up to 3 pages),
  and reproducible source code.

Action: Please paste the official Kaggle criteria/rules so I can replace this section
with the authoritative requirements.

## 2. Product Vision
Build a local-first assistant that improves communication between chronic patients and
doctors. The system should help patients explain symptoms, help doctors triage and review
changes quickly, and reduce time spent on clinical documentation.

## 3. Target Users
- Chronic patients (diabetes, hypertension, COPD, etc.)
- Grassroots/district doctors managing large patient panels
- Clinic admins (optional)

## 4. Core User Stories
Patient
1. As a patient, I can ask questions in Vietnamese about my condition and medications and
   receive understandable answers grounded in my records.
2. As a patient, I can submit new symptoms, vitals, or documents and know if a doctor
   needs to review them.
3. As a patient, I can see what the AI understood from my message before it is sent to
   the doctor (optional review step).

Doctor
1. As a doctor, I can ask the assistant about any patient without pre-selecting them and
   get a concise, record-grounded summary.
2. As a doctor, I can see which patients are urgent and why, with evidence from recent
   vitals or notes.
3. As a doctor, I can generate a draft clinical summary after a conversation and edit it
   before saving.

## 4.1 Communication Model (Decision)
Patients chat with AI first. The system performs symptom triage and safety checks.
If a dangerous situation is detected, the patient is prompted to contact a doctor
directly and the case is escalated to the doctor with an AI-generated summary.

## 5. Scope (MVP)
- Patient chat with AI (Vietnamese), grounded in patient records via RAG.
- Doctor chat that can reference any patient, with structured output and safety checks.
- Upload of PDFs/images/text to create medical records + embeddings.
- Doctor patient list, patient detail, and record history.
- Basic triage and escalation logic for urgent symptoms.
- Imaging support in MVP: X-ray, ECG, CT, MRI.

## 6. What Is Implemented (Current App)
Backend
- FastAPI app with /chat, /chat/stream, /chat/history, /chat/doctor/v2/stream,
  /chat/doctor/v2/resume, /chat/patient/v2/stream.
- Translation sandwich pipeline: Vi->En, MedGemma reasoning, En->Vi.
- RAG pipeline using pgvector (chunking, embedding, vector search).
- OCR for PDFs and images (PaddleOCR) and ingestion into records/embeddings.
- Upload endpoints for documents, chat images, patient photos, and record images.
- Doctor endpoints: patient list, patient detail, records, dashboard stats, clinical summary.
- LangGraph-based doctor and patient flows with verification, safety checks, HITL, and
  resilience (retry/circuit breaker).
- Database schema for patients, doctors, vitals, consultations, records, embeddings.

Frontend
- Role selection (doctor/patient) and demo auth context.
- Dashboard with stats and quick actions.
- Patient list and patient detail with profile photo and imaging upload.
- Patient and doctor chat UIs with SSE streaming progress.
- React Query hooks and API clients for backend endpoints.

## 7. Gaps / What To Implement Next
Product
- Direct patient-doctor messaging workflow (currently AI-only mediation).
- Doctor review queue for AI-flagged or urgent patient messages.
- Patient vitals input + history visualization.
- Full record viewer (list, filter, download, images).
- Appointment scheduling and reminders (optional but strong for chronic care).

Safety and Compliance
- Consent and data retention policies in UI and documentation.
- Audit trail UI for AI decisions and HITL approvals.

Auth and Access
- Real authentication (Supabase Auth) and role-based access control.

Competition Deliverables
- Demo video (<= 3 minutes) showing end-to-end workflows.
- Technical overview (<= 3 pages) with architecture, models, and evaluation.
- Reproducible setup instructions and scripts.
- Explicit statement of HAI-DEF model usage and how MedGemma is integrated.

## 8. Architecture Summary
Frontend (Next.js) -> API (FastAPI) -> Supabase (Postgres + pgvector + Storage)
Models:
- MedGemma for reasoning (Ollama)
- HAI-DEF model for verification/safety (Gemma 2B instruct)
- VinAI Translate (Vi<->En)
- Nomic embed text for embeddings (Ollama)

## 8.1 Image Understanding Pipeline
Goal: Use MedSigLIP for image evaluation, then MedGemma for thorough analysis.

Proposed flow:
1. Image -> MedSigLIP -> embeddings/similarity against a curated findings taxonomy.
2. Convert top-k findings into a structured "image findings" object.
3. Merge image findings + RAG patient context + vitals.
4. MedGemma generates the final analysis and patient-friendly explanation.

Output artifacts:
- Structured findings stored with the medical record.
- Final narrative stored in consultation/analysis results.

## 8.2 Deployment Strategy (Local-First + Optional API)
- Default: local-first inference for privacy and offline capability.
- Optional: remote API inference for heavy models when local compute is insufficient.
- Guardrails: PHI handling, explicit consent, and clear labeling of when data leaves
  the device/clinic.

## 8.3 Phased Deployment Plan
Phase 1: Local-only MVP for competition alignment and rapid iteration.
Phase 2: Measure latency and resource usage; identify bottlenecks.
Phase 3: Add optional API fallback for heavy models behind a feature flag.
Phase 4: Keep local as default; require explicit consent when remote inference is used.

## 9. Success Metrics (Proposed)
- Time saved per consultation (doctor note drafting).
- Reduction in response time for urgent cases.
- Patient satisfaction with clarity of answers (qualitative survey).
- Model safety: rate of unsafe responses flagged and corrected.

## 10. Open Questions
1. Do you want AI to mediate patient-doctor messages, or direct messaging with AI summaries?
2. Which HAI-DEF models (besides MedGemma) do you want to highlight for competition alignment?
3. What is the intended deployment environment (clinic server, local laptop, on-device)?
