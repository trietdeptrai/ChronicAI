# Migration Guide: Figma UI + GitHub Backend

This document explains how the two projects were merged and what changes were made.

## Overview

The merge combines:
1. **Figma App**: React + Vite SPA with beautiful UI components
2. **GitHub App**: Next.js + FastAPI full-stack application

**Result**: Next.js application with Figma UI + working backend integration

## Changes Made

### 1. Framework Conversion (Vite → Next.js)

**Before (Figma - Vite):**
```
src/
├── main.tsx              # Entry point
├── app/
│   ├── App.tsx           # Root component
│   └── components/       # All components
```

**After (Merged - Next.js):**
```
app/
├── layout.tsx            # Root layout
├── page.tsx              # Landing page
└── dashboard/
    └── page.tsx          # Dashboard page

components/
├── pages/                # Page components
└── ui/                   # UI components
```

### 2. Routing Changes

**Figma App (Client-side routing):**
- Used state to switch between tabs
- Single-page application

**Merged App (Next.js routing):**
- `/` - Landing page (role selection)
- `/dashboard` - Main dashboard (doctor or patient based on role)

### 3. Import Path Updates

All imports were updated from Vite aliases to Next.js aliases:

```typescript
// Before (Figma)
import { Button } from '@/app/components/ui/button'
import { mockData } from '@/lib/data/mockData'

// After (Merged)
import { Button } from '@/components/ui/button'
import { mockData } from '@/lib/data/mockData'
```

### 4. Component Organization

```
components/
├── pages/              # Figma page components
│   ├── DoctorDashboard.tsx
│   ├── PatientDashboard.tsx
│   ├── DashboardHome.tsx
│   ├── PatientsPage.tsx
│   ├── CalendarView.tsx
│   ├── ChatView.tsx
│   └── ...
├── ui/                 # Shadcn/ui components (from Figma)
│   ├── button.tsx
│   ├── card.tsx
│   └── ...
└── figma/              # Figma-specific utilities
    └── ImageWithFallback.tsx
```

### 5. Data & API Integration

**Preserved from GitHub:**
- `lib/api/` - API client for backend
- `lib/hooks/` - Custom React hooks
- `types/` - TypeScript types
- `contexts/` - React contexts (QueryProvider, AuthContext)

**Added from Figma:**
- `lib/data/` - Mock data for development
- `lib/imports/` - Figma-generated assets

### 6. Dependencies Merged

The `package.json` combines dependencies from both projects:

**From Figma:**
- Material-UI components
- Additional Radix UI components
- Motion animations
- React DnD
- Recharts
- More UI libraries

**From GitHub:**
- Next.js 16
- React Query
- API integration tools
- TypeScript tooling

### 7. State Management

**Role Selection:**
```typescript
// Landing page (app/page.tsx)
localStorage.setItem('userRole', 'doctor' | 'patient')

// Dashboard (app/dashboard/page.tsx)
const role = localStorage.getItem('userRole')
```

### 8. Configuration Files

**Preserved:**
- `tsconfig.json` - TypeScript configuration
- `next.config.ts` - Next.js configuration
- `tailwind.config.ts` - Tailwind CSS configuration
- `postcss.config.mjs` - PostCSS configuration

**Added:**
- `.env.local` - Environment variables (create this)

## Key Differences

| Aspect | Figma App | Merged App |
|--------|-----------|------------|
| Framework | Vite + React | Next.js 16 |
| Routing | State-based | File-based |
| Data | Mock only | Mock + Real API |
| Entry Point | `main.tsx` | `app/page.tsx` |
| Build Tool | Vite | Next.js |
| Server | Dev only | SSR capable |

## What Works Out of the Box

✅ All Figma UI components
✅ Landing page with role selection
✅ Doctor dashboard with all tabs
✅ Patient dashboard
✅ Navigation and routing
✅ Styling and animations
✅ Mock data for development

## What Needs Backend Connection

⚠️ These features require backend API to be running:

- Real patient data fetching
- AI chat functionality
- Document upload
- Authentication
- Appointment booking
- Real-time alerts

## Next Steps

### 1. Connect to Backend API

Update `lib/api/client.ts` with your API URL:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### 2. Replace Mock Data

In components, replace mock data with API calls:

```typescript
// Before
import { mockPatients } from '@/lib/data/mockData'

// After
import { usePatients } from '@/lib/hooks/use-patients'
const { data: patients } = usePatients()
```

### 3. Add Authentication

Implement proper authentication using the AuthContext:

```typescript
import { useAuth } from '@/contexts/auth-context'
const { login, logout, user } = useAuth()
```

### 4. Environment Variables

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## File Structure Reference

```
merged_project/
├── frontend/                    # Next.js app
│   ├── app/                     # App router pages
│   ├── components/              # React components
│   ├── lib/                     # Utilities & API
│   ├── types/                   # TypeScript types
│   ├── contexts/                # React contexts
│   ├── public/                  # Static assets
│   └── package.json            # Dependencies
├── api/                         # FastAPI backend (unchanged)
├── docs/                        # Documentation
└── README.md                   # Main readme
```

## Troubleshooting

### Import Errors

If you see import errors:
1. Check that the path uses `@/` prefix
2. Verify the file exists in the correct location
3. Check `tsconfig.json` has correct path mappings

### Component Not Found

Components from Figma are in `components/pages/`:
```typescript
import { DoctorDashboard } from '@/components/pages/DoctorDashboard'
```

### Styling Issues

If styles don't apply:
1. Check `globals.css` is imported in `app/layout.tsx`
2. Verify Tailwind is configured correctly
3. Check for conflicting class names

### API Connection

If API calls fail:
1. Ensure backend is running on port 8000
2. Check CORS settings in backend
3. Verify API URL in environment variables

## Development Workflow

1. **Start Backend** (in `api/` directory):
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```

2. **Start Frontend** (in `frontend/` directory):
   ```bash
   npm run dev
   ```

3. **Access App**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Additional Resources

- Original Figma README: `frontend_original_backup/README.md` (if exists)
- GitHub project docs: `docs/`
- Next.js documentation: https://nextjs.org/docs
- React Query docs: https://tanstack.com/query
