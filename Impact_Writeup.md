# MedGemma Impact Writeup Draft

## Problem statement
**[Your answer to the “Problem domain” & “Impact potential” criteria]**

**Problem Domain: The Chronic Disease Management Gap in Vietnam**
Chronic diseases (hypertension, diabetes, COPD) impose a crushing burden on the Vietnamese healthcare system, where the doctor-to-patient ratio is often critically low (approx. 8-10 doctors per 10,000 people).
*   **Doctor Burnout**: Physicians spend up to 40% of their time on administrative tasks and reviewing fragmented Electronic Health Records (EHR) rather than patient care.
*   **Patient Vulnerability**: Between visits, patients lack reliable medical guidance. They often turn to "Dr. Google," leading to anxiety or dangerous self-medication. Language barriers further exacerbate this, as most high-quality medical AI tools are English-first.

**Impact Potential:**
ChronicAI aims to bridge this gap by acting as a **force multiplier** for doctors and a **24/7 safety net** for patients.
*   **Scalability**: By automating routine monitoring, triage, and data synthesis, one doctor can effectively manage 5x-10x more patients without burnout.
*   **Democratized Access**: Bringing high-quality, MedGemma-powered medical reasoning to Vietnamese patients in their native language, powered by localizable, open-weight tooling.
*   **Safety**: Unlike generic chatbots, ChronicAI provides medically-grounded, context-aware advice that strictly adheres to safety protocols, reducing hospital readmissions through early intervention.

---

## Overall solution
**[Your answer to “Effective use of HAI-DEF models” criterion]**

**Core Architecture: HAI-DEF Powered Dual-Graph Orchestrator**
Our solution leverages **MedGemma** (a Google HAI-DEF model) as the reasoning engine for a sophisticated "Dual-Graph" architecture orchestrated by LangGraph. We do not simply "call an API"; we have built a cognitive architecture around MedGemma to maximize its clinical utility and safety.

1.  **Patient Graph (Empathetic Triage)**:
    *   Uses MedGemma to analyze symptoms against the patient's specific medical history (retrieved via RAG).
    *   **Safety-First Design**: Implements a dedicated "Symptom Triage" node. If MedGemma detects emergency signs (e.g., "chest pain"), the system short-circuits to an **Escalation Protocol**, advising immediate hospital visits rather than attempting diagnosis.
    *   **Tone adaptation**: MedGemma is prompted to speak in a supportive, non-technical Vietnamese persona.
    *   **Self-Harm Detection**: Hard-coded safety overrides combined with MedGemma's content alignment prevent engagement with self-harm ideation, directing users to helplines instead.

2.  **Doctor Graph (Clinical Decision Support)**:
    *   **Deep Reasoning**: Leverages MedGemma's fine-tuned medical knowledge to synthesize complex patient records, visualize trends from vital signs, and flag drug interactions.
    *   **Ambiguity Resolution**: Uses a "Fuzzy Matching" node to correctly identify patients even with Vietnamese typo variations (e.g., "Binh" vs "Bình"), ensuring the *correct* record is retrieved before MedGemma generates advice.

3.  **Cross-Lingual RAG**:
    *   We implement a "Translation Sandwich" pipeline. Patient queries (Vietnamese) are understood, context is retrieved (Vietnamese medical records), and then synthesized by MedGemma (English/Multilingual reasoning) before being formatted back into natural Vietnamese. This allows us to use the full reasoning power of English-centric medical fine-tunes while serving a non-English population.

---

## Technical details
**[Your answer to “Product feasibility” criterion]**

**Tech Stack & Implementation**
*   **Backend**: Python FastAPI with **LangGraph** for stateful multi-step reasoning.
*   **AI Engine**: **MedGemma** (deployed via Vast.ai/Vertex AI) and **EnViT5** (for specialized translation tasks).
*   **Database**: **Supabase** (PostgreSQL) with `pgvector` for vector similarity search (RAG).
*   **Frontend**: Next.js 14 (React) with a responsive, mobile-first design for patient accessibility.

**Feasibility & Resilience Measures**
To move from "demo" to "product-ready," we implemented robust engineering, not just happy-path AI:
1.  **Circuit Breakers**: The system uses the `pybreaker` pattern. If MedGemma prompts timeout or fail 3 times consecutively, the system degrades gracefully to a "Safe Mode," advising the user to contact a human doctor rather than stalling.
2.  **State Persistence**: LangGraph checkpoints save the conversation state to the database after every turn. This allows long-running medical consultations to be paused and resumed without losing context—critical for chronic care.
3.  **Strict JSON Enforcement**: We use a `retry_async` decorator with output parsers. If the LLM generates invalid JSON (common in smaller models), the system automatically retries with a correction prompt, ensuring the frontend always receives structured data.
4.  **Verification Layer**: A lightweight "Verificator" step runs before the main reasoning, checking the query for sufficient information. If a patient asks "My chest hurts," the system asks "Where exactly and how long?" *before* passing it to the expensive medical reasoner, optimizing both cost and clinical accuracy.
