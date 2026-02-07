# ChronicAI API (Backend) Steering Document

> **Purpose**: This document provides guidelines and best practices for AI coding agents working on the ChronicAI backend. Follow these conventions to maintain consistency and quality.

---

## Table of Contents
1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [API Design Principles](#api-design-principles)
4. [Code Organization](#code-organization)
5. [Error Handling](#error-handling)
6. [Security Guidelines](#security-guidelines)
7. [Database Conventions](#database-conventions)
8. [Testing Standards](#testing-standards)
9. [AI/ML Service Guidelines](#aiml-service-guidelines)

---

## 1. Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | FastAPI | Latest |
| **Python** | Python | 3.11+ |
| **Database** | Supabase (PostgreSQL + pgvector) | - |
| **AI Models** | MedGemma 4B, Qwen 2.5 1.5B | Via Ollama |
| **Embeddings** | nomic-embed-text | Via Ollama |
| **OCR** | PaddleOCR | Latest |

---

## 2. Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings via pydantic-settings
│   ├── dependencies.py      # Shared dependencies (auth, db sessions)
│   │
│   ├── models/              # Pydantic models (request/response schemas)
│   │   ├── __init__.py
│   │   ├── user.py          # User-related schemas
│   │   ├── patient.py       # Patient schemas
│   │   ├── doctor.py        # Doctor schemas
│   │   ├── consultation.py  # Consultation schemas
│   │   └── common.py        # Shared/base schemas
│   │
│   ├── routers/             # API route handlers (one per domain)
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── patients.py      # Patient CRUD
│   │   ├── doctors.py       # Doctor CRUD
│   │   ├── consultations.py # Consultation endpoints
│   │   ├── medical.py       # Medical AI endpoints
│   │   └── health.py        # Health check endpoints
│   │
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── patient_service.py
│   │   ├── doctor_service.py
│   │   ├── medical_ai_service.py    # MedGemma integration
│   │   ├── translation_service.py   # Qwen translation
│   │   ├── rag_service.py           # RAG pipeline
│   │   └── ocr_service.py           # PaddleOCR integration
│   │
│   ├── db/                  # Database layer
│   │   ├── __init__.py
│   │   ├── client.py        # Supabase client
│   │   └── queries/         # SQL query functions (optional)
│   │
│   └── tests/               # Unit and integration tests
│       ├── __init__.py
│       ├── test_auth.py
│       └── conftest.py
│
└── requirements.txt
```

### Key Principles:
- **One router per domain**: Keep route handlers thin, delegate to services
- **Services contain business logic**: All complex operations belong here
- **Models define contracts**: Use Pydantic for request/response validation
- **Separation of concerns**: Routers → Services → Database

---

## 3. API Design Principles

### 3.1 RESTful Conventions

| Action | HTTP Method | Endpoint Pattern | Example |
|--------|-------------|------------------|---------|
| List | GET | `/resource` | `GET /patients` |
| Get One | GET | `/resource/{id}` | `GET /patients/{patient_id}` |
| Create | POST | `/resource` | `POST /patients` |
| Update | PUT/PATCH | `/resource/{id}` | `PATCH /patients/{patient_id}` |
| Delete | DELETE | `/resource/{id}` | `DELETE /patients/{patient_id}` |

### 3.2 Naming Conventions

```python
# ✅ Good: Plural nouns for resources
GET /patients
GET /doctors
GET /consultations

# ❌ Bad: Verbs in URLs, singular nouns
GET /getPatient
GET /patient
POST /createDoctor
```

### 3.3 Versioning

Use URL versioning for breaking changes:
```python
# In main.py
app.include_router(v1_router, prefix="/api/v1")
```

### 3.4 Response Format

All API responses should follow this structure:

```python
# Success Response
{
    "success": True,
    "data": { ... },  # or list for collections
    "message": "Optional success message"
}

# Error Response
{
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable message",
        "details": { ... }  # Optional additional info
    }
}

# Paginated Response
{
    "success": True,
    "data": [...],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 150,
        "total_pages": 8
    }
}
```

---

## 4. Code Organization

### 4.1 Router Pattern

```python
# routers/patients.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services.patient_service import PatientService
from app.dependencies import get_current_user, get_patient_service

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    responses={404: {"description": "Patient not found"}}
)

@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    skip: int = 0,
    limit: int = 20,
    service: PatientService = Depends(get_patient_service)
):
    """List all patients with pagination."""
    return await service.get_all(skip=skip, limit=limit)

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    service: PatientService = Depends(get_patient_service)
):
    """Get a specific patient by ID."""
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
```

### 4.2 Service Pattern

```python
# services/patient_service.py
from app.db.client import supabase
from app.models.patient import PatientCreate, PatientUpdate

class PatientService:
    """Business logic for patient operations."""
    
    async def get_all(self, skip: int = 0, limit: int = 20):
        """Retrieve all patients with pagination."""
        response = supabase.table("patients").select("*").range(skip, skip + limit - 1).execute()
        return response.data
    
    async def get_by_id(self, patient_id: str):
        """Retrieve a single patient by ID."""
        response = supabase.table("patients").select("*").eq("id", patient_id).single().execute()
        return response.data
    
    async def create(self, data: PatientCreate):
        """Create a new patient."""
        response = supabase.table("patients").insert(data.model_dump()).execute()
        return response.data[0]
```

### 4.3 Pydantic Model Pattern

```python
# models/patient.py
from pydantic import BaseModel, Field, EmailStr
from datetime import date
from typing import Optional
from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class PatientBase(BaseModel):
    """Base patient fields shared across schemas."""
    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: GenderEnum
    phone_primary: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    email: Optional[EmailStr] = None

class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    pass

class PatientUpdate(BaseModel):
    """Schema for updating a patient (all fields optional)."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone_primary: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    
class PatientResponse(PatientBase):
    """Schema for patient API responses."""
    id: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
```

---

## 5. Error Handling

### 5.1 Custom Exception Handler

```python
# In main.py or a dedicated exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

### 5.2 Error Codes

Use consistent error codes:

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `NOT_FOUND` | Resource not found |
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | Insufficient permissions |
| `CONFLICT` | Resource already exists |
| `INTERNAL_ERROR` | Server error |
| `AI_SERVICE_ERROR` | AI model service failure |
| `DATABASE_ERROR` | Database operation failed |

---

## 6. Security Guidelines

### 6.1 Authentication

```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Validate JWT token and return current user."""
    token = credentials.credentials
    # Verify with Supabase Auth
    user = await verify_supabase_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user
```

### 6.2 Security Checklist

- [ ] Never log sensitive data (passwords, tokens, medical records)
- [ ] Validate all input using Pydantic
- [ ] Use parameterized queries (Supabase handles this)
- [ ] Implement rate limiting for public endpoints
- [ ] Encrypt sensitive fields at rest (national_id, medical records)
- [ ] Use HTTPS in production

---

## 7. Database Conventions

### 7.1 Supabase Client Usage

```python
# db/client.py
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)
```

### 7.2 Query Patterns

```python
# Simple CRUD
response = supabase.table("patients").select("*").execute()

# With filters
response = supabase.table("patients") \
    .select("*") \
    .eq("status", "active") \
    .order("created_at", desc=True) \
    .limit(20) \
    .execute()

# With relationships
response = supabase.table("consultations") \
    .select("*, patients(*), doctors(*)") \
    .execute()

# Vector similarity search (for RAG)
response = supabase.rpc(
    "match_documents",
    {"query_embedding": embedding, "match_count": 5}
).execute()
```

---

## 8. Testing Standards

### 8.1 Test Structure

```python
# tests/test_patients.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPatientEndpoints:
    """Tests for patient API endpoints."""
    
    def test_list_patients_success(self):
        """Should return list of patients."""
        response = client.get("/api/v1/patients")
        assert response.status_code == 200
        assert "data" in response.json()
    
    def test_create_patient_validation(self):
        """Should reject invalid patient data."""
        response = client.post("/api/v1/patients", json={})
        assert response.status_code == 422
```

### 8.2 Running Tests

```bash
# Run all tests
cd api
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_patients.py -v
```

---

## 9. AI/ML Service Guidelines

### 9.1 Ollama Integration Pattern

```python
# services/medical_ai_service.py
import httpx
from app.config import settings

class MedicalAIService:
    """Service for MedGemma medical AI interactions."""
    
    def __init__(self):
        self.base_url = settings.ollama_host
        self.model = settings.medical_model
    
    async def generate_response(self, prompt: str, context: str = None) -> str:
        """Generate medical AI response."""
        full_prompt = f"""You are a medical AI assistant.
        
Context: {context or 'No additional context'}

Question: {prompt}

Provide a helpful, accurate medical response."""

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                }
            )
            return response.json()["response"]
```

### 9.2 Translation Sandwich Pattern

For Vietnamese medical queries, use the translation sandwich:

```python
# services/translation_service.py
class TranslationSandwich:
    """Vietnamese ↔ English translation for medical queries."""
    
    async def process(self, vietnamese_input: str) -> str:
        # 1. Translate Vietnamese → English
        english_query = await self.translate_to_english(vietnamese_input)
        
        # 2. Process with MedGemma (English)
        english_response = await self.medical_ai.generate(english_query)
        
        # 3. Translate English → Vietnamese
        vietnamese_response = await self.translate_to_vietnamese(english_response)
        
        return vietnamese_response
```

### 9.3 RAG Pipeline

```python
# services/rag_service.py
class RAGService:
    """Retrieval-Augmented Generation for medical queries."""
    
    async def query(self, question: str) -> str:
        # 1. Generate embedding
        embedding = await self.embed_text(question)
        
        # 2. Vector similarity search
        relevant_docs = await self.search_similar(embedding, top_k=5)
        
        # 3. Build context
        context = "\n\n".join([doc["content"] for doc in relevant_docs])
        
        # 4. Generate response with context
        response = await self.medical_ai.generate(
            prompt=question,
            context=context
        )
        
        return response
```

---

## Quick Reference

### Common Commands

```bash
# Start development server
cd api
uvicorn app.main:app --reload

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Check types (if using mypy)
mypy app/
```

### Environment Variables

See `.env.example` for required variables:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OLLAMA_HOST`

---

> **Note for AI Agents**: When adding new features, always follow the existing patterns. Create router → service → models in that order. Write tests for new endpoints.
