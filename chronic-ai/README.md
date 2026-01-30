# ChronicAI

A local-first telemedicine application for chronic patients and grassroots/district-level doctors in Vietnam.

## Features

- 🏥 Remote triage and consultation
- 🔬 Medical image analysis (X-ray/ECG)
- 📝 Automated clinical documentation
- 🤖 AI-powered Vietnamese medical assistant
- 📊 Patient health monitoring

## Tech Stack

- **Backend**: FastAPI + Python 3.11+
- **Frontend**: Next.js 14 + Shadcn/UI
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI Models**: MedGemma 4B, Qwen 2.5 1.5B, nomic-embed-text
- **OCR**: PaddleOCR

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed
- Supabase account

### 1. Set up Ollama Models

```bash
cd scripts
chmod +x setup_ollama.sh
./setup_ollama.sh
```

### 2. Set up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Run the SQL in `setup_db.sql` in the Supabase SQL Editor
3. Copy your project URL and keys

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 4. Install Backend Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 5. Run Backend

```bash
cd api
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 6. Install Frontend Dependencies (Coming in Phase 6)

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
chronic-ai/
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   ├── config.py      # Settings
│   │   ├── models/        # Pydantic models
│   │   ├── services/      # Business logic
│   │   ├── routers/       # API endpoints
│   │   └── db/            # Database client
│   └── requirements.txt
├── frontend/              # Next.js frontend (Phase 6)
├── scripts/               # Setup scripts
└── setup_db.sql          # Database schema
```

## Development Status

- [x] Phase 1: Infrastructure & Database
- [ ] Phase 2: RAG Pipeline
- [ ] Phase 3: Translation Sandwich
- [ ] Phase 4: FastAPI Endpoints
- [ ] Phase 5: OCR Service
- [ ] Phase 6: Next.js Frontend
- [ ] Phase 7: Integration & Testing

## License

MIT
