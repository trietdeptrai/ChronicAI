# ChronicAI

End-to-end chronic care assistant with:
- Next.js 16 frontend (doctor and patient dashboards)
- FastAPI backend
- LangGraph orchestration
- SSE streaming updates
- Supabase (PostgreSQL + pgvector) for persistence and RAG

## 1. What You Need

- Node.js `20.19.0` (see `.nvmrc`)
- npm `10.x`
- Python `3.11.11` (see `.python-version`)
- A Supabase project (URL + keys)

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

From `chronic-ai/`:

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

## 4. Configure Environment

1. Create backend env file:
- copy `api/.env.example` to `api/.env`
- fill required values (Supabase, model/provider settings)

2. Create frontend env file `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 5. Setup Database (Supabase)

Run these SQL files in your Supabase SQL editor, in this order:

1. `setup_db.sql`
2. `setup_vector_search.sql`
3. `seed_demo_data.sql` (optional but useful for testing/demo)

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

2. SSE streaming:
- test `POST /chat/doctor/v2/stream`
- test `POST /chat/patient/v2/stream`
- confirm response streams multiple `stage` updates

3. Safety behavior:
- doctor flow can return `hitl_required`
- patient flow escalates high-risk/self-harm scenarios

4. RAG path:
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
  - rerun bootstrap script
  - confirm Node/Python versions match section 1

- Slow first AI response:
  - model/provider warm-up can take time on first request

## 10. Additional Docs

- ECG module details: `ecg_classifier/README.md`
- Design/engineering notes remain under `docs/` and other project markdown files.
