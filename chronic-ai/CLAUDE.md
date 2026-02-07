# Claude Memory - chronic-ai

## Rules

- **Always document bug fixes**: When fixing any bug, add an entry to the "Bug Fixes" section below with the date, symptom, root cause, fix applied, and files changed.

## Bug Fixes

### 2026-01-30: Fixed `__init__() got an unexpected keyword argument 'proxy'` error

**Symptom**: Patient chatbot displayed error "Lỗi: __init__() got an unexpected keyword argument 'proxy'" when sending messages.

**Root Cause**: Version mismatch between Supabase SDK and httpx:
- `supabase==2.3.4` used `gotrue==2.9.1` which passed `proxy` parameter to httpx
- `httpx==0.25.2` didn't accept `proxy` (only `proxies` plural)

**Fix Applied**:
1. Updated `api/requirements.txt`:
   - Changed `supabase==2.3.4` to `supabase>=2.10.0`
   - Removed explicit `httpx==0.25.2` (let supabase manage dependency)
   - Removed unused `ollama==0.1.6` package (code uses httpx directly for Ollama API)

2. Reinstalled dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   pip uninstall ollama -y
   ```

3. Final versions installed:
   - supabase: 2.16.0
   - gotrue: 2.12.4
   - httpx: 0.28.1 (now accepts `proxy` parameter)

**Files Changed**:
- `api/requirements.txt`

## Project Notes

### Architecture
- Backend: FastAPI with async endpoints
- Database: Supabase (PostgreSQL + pgvector)
- AI Pipeline: Translation Sandwich (Vietnamese ↔ English) + MedGemma for medical reasoning
- Uses httpx directly for Ollama API calls (not the ollama Python package)
