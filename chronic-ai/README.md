# ChronicAI - Merged Frontend

This project combines the Figma-designed UI with the ChronicAI backend into a unified Next.js application.

## Project Structure

```
chronic-ai/
├── frontend/              # Next.js frontend (merged)
│   ├── app/              # Next.js app directory
│   │   ├── dashboard/    # Main dashboard pages
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Landing page (role selection)
│   │   └── globals.css   # Global styles
│   ├── components/       # React components
│   │   ├── pages/        # Page components from Figma
│   │   ├── ui/           # UI components (shadcn/ui + custom)
│   │   └── figma/        # Figma-specific components
│   ├── lib/              # Utilities and data
│   │   ├── api/          # API client for backend
│   │   ├── hooks/        # Custom React hooks
│   │   ├── data/         # Mock data
│   │   └── utils.ts      # Utility functions
│   ├── types/            # TypeScript type definitions
│   └── contexts/         # React contexts
└── api/                  # Python FastAPI backend
    └── app/              # Backend application code
```

## Features

### Figma UI Components
- **DoctorDashboard**: Complete doctor interface with patient management
- **PatientDashboard**: Patient view with health records
- **DashboardHome**: Overview with stats and charts
- **PatientsPage**: Patient list and detail views
- **CalendarView**: Appointment scheduling
- **ChatView**: AI chat interface
- **DocumentUpload**: Medical document management
- **SettingsPage**: User settings and preferences

### Backend Integration
- **API Client**: Ready-to-use API integration (`lib/api/`)
- **React Query**: Data fetching and caching
- **TypeScript Types**: Full type safety
- **Auth Context**: User authentication state management

## Getting Started

### Prerequisites
- Node.js 20+ 
- npm or pnpm
- Python 3.11+ (for backend)

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
pnpm install
```

3. Run the development server:
```bash
npm run dev
# or
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000)

### Backend Setup

1. Navigate to the api directory:
```bash
cd api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the backend:
```bash
uvicorn app.main:app --reload
```

## User Roles

The application supports two user roles:

1. **Doctor** (`/dashboard` after selecting "Bác sĩ")
   - Manage multiple patients
   - View patient records
   - Upload and analyze medical documents
   - AI-assisted clinical decision support
   - Alerts and monitoring

2. **Patient** (`/dashboard` after selecting "Bệnh nhân")
   - View personal health records
   - Ask AI about diagnosis and medications
   - Receive monitoring reminders
   - Schedule appointments

## Technology Stack

### Frontend
- **Next.js 16**: React framework with app router
- **React 19**: UI library
- **TypeScript**: Type safety
- **Tailwind CSS 4**: Styling
- **Radix UI**: Accessible UI components
- **React Query**: Server state management
- **Recharts**: Data visualization
- **Lucide React**: Icons

### Backend (from original project)
- **FastAPI**: Python web framework
- **PostgreSQL**: Database
- **LangChain**: AI integration
- **Ollama**: Local LLM support

## API Integration

The frontend is configured to work with the backend API. Update the API base URL in `lib/api/client.ts`:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Components

### Landing Page (`app/page.tsx`)
- Role selection interface
- Stores user role in localStorage
- Redirects to dashboard

### Dashboard (`app/dashboard/page.tsx`)
- Checks user role from localStorage
- Renders appropriate dashboard (Doctor/Patient)
- Handles logout

### Doctor Dashboard (`components/pages/DoctorDashboard.tsx`)
- Sidebar navigation
- Alert panel
- Dynamic content based on selected tab
- Patient management

### Patient Dashboard (`components/pages/PatientDashboard.tsx`)
- Personal health overview
- AI chat for health questions
- Medical timeline
- Appointment booking

## Development Notes

### Import Paths
The project uses the `@/` alias for imports:
- `@/components/*` - React components
- `@/lib/*` - Utilities, hooks, API
- `@/types/*` - TypeScript types
- `@/contexts/*` - React contexts

### Mock Data
Mock data is available in `lib/data/mockData.ts` for development without backend.

### Styling
- Global styles in `app/globals.css`
- Tailwind configuration in `tailwind.config.ts`
- Component-specific styles use Tailwind utility classes

## Building for Production

```bash
cd frontend
npm run build
npm start
```

## Original Projects

- **Figma Design**: Chronic Care Management App UI
- **Backend**: ChronicAI - AI-powered chronic disease management

## License

See original project licenses.

## Support

For issues or questions:
1. Check the documentation in `/docs`
2. Review API documentation at `/api/docs`
3. Consult the original project READMEs in `frontend_original_backup/`
