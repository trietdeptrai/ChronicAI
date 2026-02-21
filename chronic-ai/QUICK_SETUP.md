# Quick Setup Guide for ChronicAI Demo

Follow these steps to get the AI chat working locally.

## Prerequisites

- [Ollama](https://ollama.ai) installed
- Supabase account with project (credentials already in `.env`)
- Node.js 18+ and Python 3.11+

---

## Step 1: Set Up Database (Supabase)

Go to your Supabase project SQL Editor and run these scripts **in order**:

1. **Create tables**: Copy and run `setup_db.sql`
2. **Create vector search function**: Copy and run `setup_vector_search.sql`
3. **Seed demo data**: Copy and run `seed_demo_data.sql`

This creates the demo patient (UUID: `11111111-1111-4111-a111-111111111111`) with:
- Medical history (diabetes type 2, hypertension)
- Vital signs (last 7 days of blood pressure, glucose readings)
- Medical records (prescriptions, lab results, doctor notes)

---

## Step 2: Install Ollama Models

```bash
# Start Ollama (if not running)
ollama serve

# In another terminal, pull the required models:
ollama pull alibayram/medgemma         # Medical reasoning
ollama pull nomic-embed-text           # Embeddings (~280MB)
```

Or run the setup script:
```bash
cd chronic-ai/scripts
chmod +x setup_ollama.sh
./setup_ollama.sh
```

---

## Step 3: Start Backend API

```bash
cd chronic-ai/api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will run at `http://localhost:8000`

Check health: `http://localhost:8000/health` - should show all models available.

---

## Step 4: Start Frontend

```bash
cd chronic-ai/frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:3000`

---

## Step 5: Test the Chat

1. Open `http://localhost:3000`
2. Click "Bệnh nhân" (Patient) to enter as demo patient
3. Go to Chat page
4. Try asking: "Huyết áp của tôi thế nào?" (How is my blood pressure?)

The AI will:
1. Translate your Vietnamese question to English
2. Search the patient's medical records for context
3. Generate a medical response using MedGemma
4. Translate the response back to Vietnamese

---

## Troubleshooting

### "Invalid patient_id format" error
- Make sure you've run `seed_demo_data.sql` in Supabase
- Hard refresh the browser (Cmd+Shift+R or Ctrl+Shift+R)

### "Ollama not running" error
- Start Ollama: `ollama serve`
- Check models: `ollama list`

### Slow first response
- First request takes longer because models need to load into memory
- Subsequent requests are faster

### Check API health
```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "ollama": true,
  "models": {
    "translation_model": true,
    "medical_model": true,
    "embedding_model": true
  }
}
```

---

## Demo Data Summary

**Demo Patient**: Trần Thị Bình
- UUID: `11111111-1111-4111-a111-111111111111`
- Conditions: Diabetes Type 2, Hypertension Stage 1
- Medications: Metformin 500mg, Amlodipine 5mg
- Allergies: Penicillin, Sulfonamide

**Demo Doctor**: BS. Nguyễn Văn An
- UUID: `22222222-2222-4222-a222-222222222222`
- Specialty: Endocrinology - Diabetes
