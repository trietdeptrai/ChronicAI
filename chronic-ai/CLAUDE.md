# Claude Memory - chronic-ai

## Rules

- **Always document bug fixes**: When fixing any bug, add an entry to the "Bug Fixes" section below with the date, symptom, root cause, fix applied, and files changed.

## Bug Fixes

### 2026-02-10: Fixed React 19 peer dependency conflict with `react-popper`

**Symptom**: `npm install` failed with `ERESOLVE` citing `react-popper@2.3.0` peer dependency requiring React `^16.8 || ^17 || ^18` while project uses React 19.

**Root Cause**: `react-popper@2.3.0` does not support React 19, and the package was unused in frontend code.

**Fix Applied**:
1. Removed `react-popper` from frontend dependencies.
2. Reinstalled dependencies without legacy peer override flags.

**Files Changed**:
- `frontend/package.json`
- `frontend/package-lock.json`

### 2026-02-10: Fixed `lucide-react` missing icon module errors at runtime

**Symptom**: Next.js build/dev failed with module-not-found errors for `lucide-react` icon files such as:
- `chart-no-axes-column.js`
- `chart-no-axes-column-increasing.js`
- `chart-no-axes-column-decreasing.js`

**Root Cause**: Installed `lucide-react@0.563.0` package contents were inconsistent with its export map in this environment.

**Fix Applied**:
1. Pinned `lucide-react` to `0.562.0` (stable package contents).
2. Updated lockfile resolution accordingly.

**Files Changed**:
- `frontend/package.json`
- `frontend/package-lock.json`

### 2026-02-10: VS Code terminal could not find `node`/`npm` while external terminal worked

**Symptom**: `where.exe node` and `where.exe npm` failed in VS Code terminal but worked outside VS Code.

**Root Cause**:
1. PATH contained `C:\Program Files\nodejs\node.exe` (file path) instead of `C:\Program Files\nodejs` (directory path).
2. VS Code terminal session retained stale environment values.

**Fix Applied**:
1. Corrected user PATH to include `C:\Program Files\nodejs` and removed `...\node.exe`.
2. Restarted VS Code terminal/session to pick updated environment variables.

**Files Changed**:
- No repository files changed (machine environment fix).

### 2026-02-10: Fixed Next.js module casing conflicts after branch switch (`D:\` vs `d:\`)

**Symptom**: `npm run dev` showed repeated warnings/errors:
- "There are multiple modules with names that only differ in casing"
- Import traces into `next/dist/shared/lib/*`
- In some runs, follow-on resolution errors (for example `Can't resolve 'tailwindcss' in ...\chronic-ai`)

**Root Cause**:
1. Mixed absolute path casing in module graph (`D:\...` and `d:\...`) after switching branches/restarting dev server.
2. Stale frontend build cache (`.next` and webpack cache) preserved old path references.
3. Dev server sometimes started from inconsistent working directory/session.

**Fix Applied**:
1. Stopped all Node dev processes.
2. Cleared frontend caches:
   - `frontend/.next`
   - `frontend/node_modules/.cache`
3. Reinstalled frontend dependencies on the current branch.
4. Started dev server from `frontend` using consistent path casing and command:
   - `npm run dev -- -p 3005`

**Files Changed**:
- No repository files changed (runtime/cache cleanup only).

### 2026-02-08: React 19 conflict with react-day-picker v8

**Symptom**: `npm install` failed with `ERESOLVE` because `react-day-picker@8.10.1` only supports React <=18.

**Root Cause**: The project uses React 19, which is outside react-day-picker v8 peer dependency range.

**Fix Applied**:
1. Upgraded `react-day-picker` to v9.
2. Updated Calendar component to use the v9 `Chevron` component API.

**Files Changed**:
- `frontend/package.json`
- `frontend/components/calendar.tsx`

### 2026-02-07: Fixed TypeScript error for lucide-react missing declarations

**Symptom**: TypeScript error "Could not find a declaration file for module 'lucide-react'" in frontend components (e.g. message-bubble.tsx).

**Root Cause**: Installed `lucide-react@0.563.0` package does not include its published `.d.ts` in `node_modules/dist`, so TS can’t resolve types.

**Fix Applied**:
1. Added a local declaration file with real icon/component typings to satisfy TypeScript.

**Files Changed**:
- `frontend/types/lucide-react.d.ts`

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
