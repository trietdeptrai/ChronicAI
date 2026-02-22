# Quick Start Guide

Get the merged ChronicAI application running in 5 minutes!

## Prerequisites

- Node.js 20+ installed
- npm or pnpm installed
- (Optional) Python 3.11+ for backend

## Frontend Only (with Mock Data)

Perfect for UI development and testing without backend setup.

### Steps

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open browser:**
   - Go to http://localhost:3000
   - Select "Bác sĩ" (Doctor) or "Bệnh nhân" (Patient)
   - Explore the UI with mock data

✅ **That's it!** The app will use mock data from `lib/data/mockData.ts`

## Full Stack (Frontend + Backend)

For complete functionality with AI features and real data.

### Backend Setup

1. **Navigate to API directory:**
   ```bash
   cd api
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

4. **Set up database:**
   ```bash
   # Follow instructions in api/QUICK_SETUP.md
   ```

5. **Start backend:**
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```
   Backend will run on http://localhost:8000

### Frontend Setup (with Backend)

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Create environment file:**
   ```bash
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

3. **Install dependencies:**
   ```bash
   npm install
   ```

4. **Start frontend:**
   ```bash
   npm run dev
   ```

5. **Open browser:**
   - Go to http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

## Features Available

### With Mock Data Only
✅ All UI components and layouts
✅ Navigation and routing
✅ Visual interactions
✅ Dashboard views
✅ Patient list views
✅ Calendar interface
❌ AI chat (needs backend)
❌ Document upload (needs backend)
❌ Real data persistence (needs backend)

### With Full Stack
✅ Everything above, plus:
✅ AI-powered chat
✅ Document analysis
✅ Real patient data
✅ Database persistence
✅ Advanced analytics

## Common Commands

### Frontend
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run linter
```

### Backend
```bash
uvicorn app.main:app --reload     # Development mode
uvicorn app.main:app              # Production mode
pytest                             # Run tests
```

## Default Ports

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Project Structure

```
.
├── frontend/          # Next.js application
│   ├── app/          # Pages and routes
│   ├── components/   # React components
│   └── lib/          # Utils and API
└── api/              # Python backend
    └── app/          # FastAPI application
```

## Troubleshooting

### Port Already in Use

**Frontend (3000):**
```bash
# Kill process using port 3000
lsof -ti:3000 | xargs kill -9  # Mac/Linux
# Or use a different port
npm run dev -- -p 3001
```

**Backend (8000):**
```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9  # Mac/Linux
# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Module Not Found

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API Connection Failed

1. Check backend is running: http://localhost:8000/docs
2. Verify `.env.local` has correct API URL
3. Check CORS settings in backend

### Styling Not Working

```bash
# Rebuild Tailwind
npm run build
```

## Next Steps

1. **Explore the UI**: Navigate through different tabs and views
2. **Check Documentation**: Read `README.md` and `MIGRATION_GUIDE.md`
3. **Review Components**: Look at `components/pages/` to understand structure
4. **Connect Backend**: Follow Full Stack setup for complete features
5. **Customize**: Modify components and add your own features

## Need Help?

- Check `README.md` for detailed documentation
- Review `MIGRATION_GUIDE.md` for technical details
- See `docs/` folder for API documentation
- Check original project documentation in `frontend_original_backup/`

## User Accounts (Mock Data)

When using mock data, you can explore:

**Doctor View:**
- Multiple patient records
- Patient management interface
- Clinical tools

**Patient View:**
- Personal health dashboard
- Medical timeline
- Health metrics

No login required - just select a role and start exploring!
