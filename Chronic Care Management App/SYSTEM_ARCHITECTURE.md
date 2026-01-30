# MediCare Pro - System Architecture

## Overview
MediCare Pro is a comprehensive chronic disease management platform designed for remote care of patients with:
- Hypertension (Cao huyết áp)
- Diabetes (Tiểu đường)
- Cardiovascular diseases (Tim mạch)
- Cancer (Ung thư)
- Asthma (Hen suyễn)

---

## 1. System Architecture

### Frontend Architecture (Current Implementation)
```
┌─────────────────────────────────────────────────────────┐
│                    User Interface Layer                  │
│  ┌──────────────┐              ┌──────────────┐         │
│  │   Doctor     │              │   Patient    │         │
│  │  Dashboard   │              │  Dashboard   │         │
│  └──────────────┘              └──────────────┘         │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│              Component Layer (React)                     │
│  • PatientList        • PatientDetail                   │
│  • MedicalTimeline    • AIChat                          │
│  • DocumentUpload     • AlertPanel                      │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│              Data Layer (Mock/Local State)               │
│  • mockData.ts: Patients, Records, Alerts               │
│  • AI Response Templates                                 │
└─────────────────────────────────────────────────────────┘
```

### Production Architecture (Future)
```
┌─────────────────────────────────────────────────────────┐
│                     Client Layer                         │
│              React Frontend (Vite + TypeScript)          │
└─────────────────────────────────────────────────────────┘
                           │
                    [HTTPS/WSS]
                           │
┌─────────────────────────────────────────────────────────┐
│                   Backend Layer                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  API Gateway (Node.js / Express / NestJS)        │  │
│  │  • Authentication & Authorization                │  │
│  │  • Rate Limiting & Security                      │  │
│  │  • Request Validation                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Medical Services                                │  │
│  │  • Patient Management Service                    │  │
│  │  • Medical Record Service                        │  │
│  │  • Document Processing Service                   │  │
│  │  • Alert & Notification Service                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                    [Internal API]
                           │
┌─────────────────────────────────────────────────────────┐
│                   AI Processing Layer                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  AI/ML Services                                   │  │
│  │  • Medical NLP (Text Extraction)                 │  │
│  │  • Image Analysis (CT/X-ray/ECG)                 │  │
│  │  • Clinical Decision Support                     │  │
│  │  • Risk Assessment Engine                        │  │
│  │  • Conversational AI (Medical Chatbot)           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Technologies:                                           │
│  • OpenAI GPT-4 / GPT-4 Vision (or similar)             │
│  • Medical-specific LLMs (BioGPT, Med-PaLM)             │
│  • OCR: Tesseract / Azure Computer Vision               │
│  • DICOM Processing: Cornerstone.js / pydicom           │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   Data Storage Layer                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Database (PostgreSQL / MongoDB)                 │  │
│  │  • Patient profiles                              │  │
│  │  • Medical records (structured)                  │  │
│  │  • Lab results                                   │  │
│  │  • Medication history                            │  │
│  │  • User accounts & permissions                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  File Storage (S3 / Azure Blob / GCS)            │  │
│  │  • Medical images (DICOM, JPEG, PNG)             │  │
│  │  • Scanned documents (PDF)                       │  │
│  │  • ECG files                                     │  │
│  │  • Encrypted with AES-256                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Vector Database (Pinecone / Weaviate)           │  │
│  │  • Indexed medical records for AI retrieval      │  │
│  │  • Embeddings for semantic search                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Core Features

### 2.1 Patient Profile System
**Data Model:**
```typescript
Patient {
  id: string
  name: string
  age: number
  gender: 'M' | 'F'
  diseases: DiseaseType[]  // Multiple chronic conditions
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  lastVisit: Date
  nextFollowUp: Date
  contactInfo: { phone, email, address }
  emergencyContact: { name, phone, relation }
}
```

**Features:**
- Multi-disease tracking
- Risk stratification (low → critical)
- Automated follow-up scheduling
- Disease-specific icons and badges

---

### 2.2 Medical Document Pipeline

```
Upload → Parse → Extract → Summarize → Index → Alert
```

**Step 1: Upload**
- Drag-and-drop interface
- Support: PDF, JPG, PNG, DICOM
- File validation and size limits
- Document type classification

**Step 2: Parse**
- OCR for scanned documents (Tesseract / Azure CV)
- DICOM parsing for medical images
- PDF text extraction

**Step 3: Extract**
AI extracts:
- Diagnoses
- Medications (name, dosage, frequency)
- Lab results (test name, value, normal range)
- Vitals (BP, glucose, HR, weight)
- Imaging findings
- Recommendations

**Step 4: Summarize**
Generate bullet-point clinical summaries:
- Current condition assessment
- Abnormal findings
- Risk factors
- Changes from previous records

**Step 5: Index**
- Store in database with timestamps
- Create vector embeddings for AI retrieval
- Link to patient timeline

**Step 6: Alert**
Automated alerts for:
- Critical values (BP >180/120, Glucose >300)
- Abnormal trends
- Imaging abnormalities
- Medication conflicts

---

### 2.3 Multi-Modal AI Handling

#### Text Analysis
- **Input:** Medical records, discharge summaries, lab reports
- **Processing:** NLP extraction, entity recognition
- **Output:** Structured data + summary

#### Image Analysis
- **Input:** X-rays, CT scans, ultrasounds
- **Processing:** GPT-4 Vision / Medical imaging AI
- **Output:** Findings description, abnormality detection

#### ECG Analysis
- **Input:** ECG images or DICOM files
- **Processing:** Computer vision + ML models
- **Output:** Rhythm analysis, ST changes, arrhythmia detection

#### Lab Results
- **Input:** Lab PDFs or structured data
- **Processing:** Value extraction, threshold comparison
- **Output:** Abnormal flagging, trend analysis

---

### 2.4 Doctor Dashboard

**Components:**
1. **Patient List (Left Sidebar)**
   - Search and filter
   - Risk-level badges
   - Disease icons
   - Next follow-up date

2. **Patient Detail (Main Area)**
   - **Overview Tab:** Latest visit summary, vitals, medications
   - **Timeline Tab:** Chronological medical history
   - **AI Chat Tab:** Clinical assistant for analysis
   - **Upload Tab:** Document upload interface

3. **Alert Panel**
   - Critical alerts (top priority)
   - Warnings
   - Info notifications
   - Read/unread status

**Workflows:**
- Select patient → View comprehensive history
- Upload document → AI auto-processes → Review summary
- Chat with AI → Get clinical insights
- Receive alerts → Take action

---

### 2.5 Patient Dashboard

**Components:**
1. **Personal Header**
   - Name, age, conditions
   - Risk level
   - Next appointment

2. **Health Overview**
   - Latest visit summary
   - Current medications
   - Recent lab results

3. **Timeline**
   - Personal medical history
   - Test results
   - Prescriptions

4. **AI Assistant**
   - Patient-friendly explanations
   - Medication guidance
   - Symptom advice
   - When to see doctor

**Key Differences from Doctor View:**
- Simplified language
- No clinical jargon
- Educational focus
- Reassuring tone
- Limited to own records only

---

### 2.6 AI Chat Interface

#### Doctor Mode
**Capabilities:**
- Analyze patient records
- Compare timelines ("Is patient worse than last month?")
- Interpret imaging ("Is there ST-elevation in ECG?")
- Flag risks ("Does patient need immediate intervention?")
- Suggest follow-ups

**Sample Questions:**
- "Hôm nay bệnh nhân có cao huyết áp không?"
- "Chest X-ray có mờ không? Có cần chỉ định CT không?"
- "ECG có ST-elevation không?"
- "So với lần trước, tình trạng có xấu hơn không?"

**Response Format:**
- Clinical assessment
- Supporting data
- Risk flags (⚠️)
- Recommendations
- Disclaimer: "AI không thay thế quyết định lâm sàng"

#### Patient Mode
**Capabilities:**
- Explain diseases in simple terms
- Explain medications
- Interpret lab results
- Provide lifestyle advice
- Warning signs

**Sample Questions:**
- "Cao huyết áp là gì?"
- "Thuốc của tôi có tác dụng gì?"
- "Tôi nên ăn uống như thế nào?"
- "Khi nào cần gặp bác sĩ gấp?"

**Response Format:**
- Plain language
- Analogies and examples
- Visual indicators (✅ ❌ 🚨)
- Reassuring tone
- Disclaimer: "Tôi chỉ cung cấp thông tin, không thay thế bác sĩ"

---

### 2.7 Alert & Follow-up System

#### Alert Types
1. **Critical (Red)**
   - EF <40% (heart failure)
   - BP >180/120
   - Glucose >300 mg/dL
   - New imaging abnormalities
   - **Action:** Immediate notification

2. **Warning (Orange)**
   - Abnormal lab trends
   - HbA1c not at target
   - ECG changes (non-emergency)
   - **Action:** Review within 24-48h

3. **Info (Blue)**
   - Upcoming appointments
   - Medication refill reminders
   - Routine follow-ups

#### Follow-up Scheduling
- **Automatic:** Based on disease severity and protocols
  - High risk: Every 2-4 weeks
  - Medium risk: Every 1-2 months
  - Low risk: Every 3-6 months
- **Manual override:** Doctor can adjust
- **Reminders:** SMS/Email/Push notifications

---

## 3. Technology Stack

### Current (Prototype)
- **Frontend:** React 18 + TypeScript
- **Build:** Vite
- **Styling:** Tailwind CSS v4
- **Icons:** Lucide React
- **State:** React hooks (useState)
- **Data:** Mock data in TypeScript

### Production Recommendation

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS
- React Query (data fetching)
- Zustand (state management)
- React Router (routing)

**Backend:**
- Node.js + NestJS (or Express)
- PostgreSQL (structured medical data)
- MongoDB (documents, logs)
- Redis (caching, sessions)
- AWS S3 / Azure Blob (file storage)

**AI/ML:**
- OpenAI GPT-4 / GPT-4 Vision
- LangChain (AI orchestration)
- Pinecone / Weaviate (vector DB)
- Hugging Face models (medical NLP)

**Infrastructure:**
- Docker + Kubernetes
- AWS / Azure / GCP
- Load balancing
- CDN for static assets

**Security:**
- End-to-end encryption
- HIPAA compliance (US) / GDPR (EU)
- Role-based access control (RBAC)
- Audit logging
- Data anonymization for AI training

---

## 4. Security & Compliance

### Data Protection
- **Encryption at rest:** AES-256
- **Encryption in transit:** TLS 1.3
- **Database:** Field-level encryption for PII
- **File storage:** Encrypted buckets

### Access Control
- **Authentication:** OAuth 2.0 / JWT
- **Authorization:** RBAC
  - Doctor: Full access to assigned patients
  - Patient: Own records only
  - Admin: System management

### Compliance
- **HIPAA (US):** Protected Health Information (PHI)
- **GDPR (EU):** Right to erasure, data portability
- **ISO 27001:** Information security
- **Audit logs:** All access and modifications tracked

---

## 5. AI Capabilities (Detailed)

### Medical Record Understanding
**Input:** Unstructured text (discharge summary, visit notes)

**Processing:**
1. Entity extraction (NER)
   - Diseases: ICD-10 codes
   - Medications: RxNorm codes
   - Procedures: CPT codes
2. Temporal information
3. Negation detection ("no signs of...")
4. Relationship extraction (medication → disease)

**Output:**
```json
{
  "summary": "Patient with uncontrolled hypertension...",
  "diagnoses": ["Hypertension stage 2", "Type 2 DM"],
  "medications": [
    { "name": "Amlodipine", "dosage": "10mg", "frequency": "daily" }
  ],
  "abnormal_findings": ["BP 165/98", "HbA1c 8.1%"],
  "risk_factors": ["Uncontrolled BP", "Poor glycemic control"],
  "recommendations": ["Increase antihypertensive", "Add statin"]
}
```

### Clinical Decision Support
**Scenario:** New ECG uploaded with ST-segment changes

**AI Analysis:**
1. Detect ST-segment elevation/depression
2. Localize to ECG leads (anterior, inferior, lateral)
3. Assess urgency:
   - STEMI (ST elevation myocardial infarction) → Emergency
   - NSTEMI or ischemia → Urgent
   - Stable changes → Follow-up
4. Compare to previous ECGs (if available)
5. Generate alert and recommendation

**Response:**
```
⚠️ ECG ANALYSIS - URGENT

Findings:
• ST depression 1-2mm in leads V3-V6
• T-wave inversion in V3-V4
• No acute ST elevation

Interpretation:
Suggestive of subendocardial ischemia (NSTEMI vs. chronic CAD)

Comparison to previous ECG (3 months ago):
NEW CHANGES - ST changes were not present before

Recommendation:
1. Check troponin levels STAT
2. Consider cardiology consult
3. If troponin elevated → ACS protocol
4. If negative → stress test or CT coronary angiography

⚠️ Not an emergency but requires urgent evaluation within 24 hours.
```

---

## 6. User Workflows

### Doctor Workflow: New Patient Visit
1. Select patient from list
2. Review timeline (past history)
3. Upload new documents (visit notes, labs, ECG)
4. AI auto-processes → generates summary
5. Review AI summary and alerts
6. Chat with AI for clinical insights
7. Update treatment plan
8. Set follow-up date
9. System auto-generates reminders

### Doctor Workflow: Emergency Alert
1. Receive notification (push/email)
2. Click alert → goes directly to patient
3. View critical values/findings
4. Review AI analysis
5. Contact patient
6. Document intervention
7. Adjust monitoring plan

### Patient Workflow: Check Health Status
1. Log in to patient dashboard
2. View latest visit summary
3. Check medication list
4. Ask AI: "What does my HbA1c mean?"
5. AI explains in simple terms
6. View upcoming appointment
7. Set reminder

### Patient Workflow: Symptom Concern
1. Notice symptom (chest pain, high BP reading)
2. Go to AI chat
3. Ask: "Huyết áp 170/100, tôi có cần đi bệnh viện không?"
4. AI assesses urgency
5. AI recommends immediate action if critical
6. Patient contacts doctor or goes to ER

---

## 7. Future Enhancements

### Phase 1 (Current) - Prototype
✅ Multi-patient management
✅ Document upload
✅ AI chat (simulated)
✅ Timeline view
✅ Alert system

### Phase 2 - Backend Integration
- Real backend API
- Database persistence
- File upload to cloud storage
- User authentication

### Phase 3 - Advanced AI
- Real AI integration (OpenAI GPT-4)
- Image analysis (CT, X-ray, ECG)
- Predictive analytics (risk models)
- Real-time monitoring integration

### Phase 4 - Telemedicine
- Video consultations
- Screen sharing for image review
- Prescription e-signing
- Insurance integration

### Phase 5 - Wearables & IoT
- Integration with glucose monitors
- Blood pressure monitors
- Smartwatch (heart rate, activity)
- Automated data sync

### Phase 6 - Analytics & Research
- Population health analytics
- Treatment outcome analysis
- Anonymized data for research
- ML model improvement

---

## 8. Disclaimer

⚠️ **IMPORTANT MEDICAL DISCLAIMER**

This system is designed as a **clinical decision support tool** and **patient education platform**. It does NOT:

- Replace the judgment of licensed healthcare professionals
- Provide definitive diagnoses
- Replace in-person medical examination
- Guarantee accuracy of AI-generated insights
- Replace emergency medical services

**All clinical decisions must be made by qualified healthcare providers.**

**For production use, this system requires:**
- Medical device certification (FDA / CE Mark)
- Clinical validation studies
- Peer-reviewed publication of AI algorithms
- Professional liability insurance
- Compliance with local medical regulations

---

## Contact & Development

This prototype demonstrates the core functionality of a chronic disease management system with AI assistance. For production deployment, a full development team including:
- Medical professionals (physicians, nurses)
- Software engineers
- Data scientists / ML engineers
- UX/UI designers
- Regulatory compliance experts
- Security experts

would be required to build, validate, and deploy a compliant medical system.
