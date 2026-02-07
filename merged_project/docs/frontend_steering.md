# ChronicAI Frontend Steering Document

> **Purpose**: This document provides guidelines and best practices for AI coding agents working on the ChronicAI frontend. Follow these conventions to maintain consistency and quality.

---

## Table of Contents
1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Routing & Navigation](#routing--navigation)
4. [Component Patterns](#component-patterns)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Styling Guidelines](#styling-guidelines)
8. [Accessibility](#accessibility)
9. [Testing Standards](#testing-standards)
10. [Performance Optimization](#performance-optimization)

---

## 1. Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | Next.js | 14 (App Router) |
| **UI Library** | Shadcn/UI | Latest |
| **Styling** | Tailwind CSS | 3.x |
| **Language** | TypeScript | 5.x |
| **State** | React Context + TanStack Query | - |
| **Forms** | React Hook Form + Zod | - |

---

## 2. Project Structure

```
frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth route group
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   ├── (dashboard)/              # Protected dashboard routes
│   │   ├── layout.tsx            # Dashboard layout with sidebar
│   │   ├── page.tsx              # Dashboard home
│   │   ├── patients/
│   │   │   ├── page.tsx          # Patient list
│   │   │   └── [id]/
│   │   │       └── page.tsx      # Patient detail
│   │   ├── consultations/
│   │   └── settings/
│   ├── api/                      # API routes (if needed)
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Landing page
│   └── globals.css               # Global styles
│
├── components/                   # Shared components
│   ├── ui/                       # Shadcn/UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── ...
│   ├── chat/                     # Chat-specific components
│   │   ├── chat-interface.tsx
│   │   ├── message-bubble.tsx
│   │   └── chat-input.tsx
│   ├── medical/                  # Medical-specific components
│   │   ├── vital-signs-card.tsx
│   │   ├── medical-image-viewer.tsx
│   │   └── symptom-checker.tsx
│   ├── sidebar/                  # Navigation components
│   │   ├── sidebar.tsx
│   │   └── nav-item.tsx
│   └── shared/                   # General shared components
│       ├── page-header.tsx
│       ├── loading-spinner.tsx
│       └── error-boundary.tsx
│
├── lib/                          # Utilities and configurations
│   ├── api/                      # API client functions
│   │   ├── client.ts             # Base API client
│   │   ├── patients.ts           # Patient API calls
│   │   ├── consultations.ts      # Consultation API calls
│   │   └── auth.ts               # Auth API calls
│   ├── hooks/                    # Custom React hooks
│   │   ├── use-auth.ts
│   │   ├── use-patients.ts
│   │   └── use-debounce.ts
│   ├── utils/                    # Utility functions
│   │   ├── cn.ts                 # Classname merger
│   │   ├── format.ts             # Date/number formatters
│   │   └── validation.ts         # Validation helpers
│   └── constants.ts              # App constants
│
├── types/                        # TypeScript type definitions
│   ├── api.ts                    # API response types
│   ├── patient.ts                # Patient types
│   ├── doctor.ts                 # Doctor types
│   └── consultation.ts           # Consultation types
│
├── contexts/                     # React contexts
│   ├── auth-context.tsx
│   └── theme-context.tsx
│
└── public/                       # Static assets
    ├── images/
    └── icons/
```

### Key Principles:
- **App Router**: Use Next.js 14 App Router with Server Components by default
- **Colocation**: Keep related files close (route-specific components in route folders)
- **Feature folders**: Group by feature in `components/` when appropriate
- **Type safety**: TypeScript everywhere, no `any` types

---

## 3. Routing & Navigation

### 3.1 Route Groups

Use route groups `(folder)` for layout sharing without affecting URL:

```
app/
├── (auth)/              # /login, /register (no layout)
├── (dashboard)/         # /patients, /consultations (with dashboard layout)
└── (marketing)/         # /, /about, /pricing (marketing layout)
```

### 3.2 Page Component Pattern

```typescript
// app/(dashboard)/patients/page.tsx
import { Suspense } from "react"
import { PatientList } from "@/components/patients/patient-list"
import { PatientListSkeleton } from "@/components/patients/patient-list-skeleton"
import { PageHeader } from "@/components/shared/page-header"

export const metadata = {
  title: "Patients | ChronicAI",
  description: "Manage your patients"
}

export default function PatientsPage() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Bệnh nhân" 
        description="Quản lý danh sách bệnh nhân"
      />
      <Suspense fallback={<PatientListSkeleton />}>
        <PatientList />
      </Suspense>
    </div>
  )
}
```

### 3.3 Dynamic Routes

```typescript
// app/(dashboard)/patients/[id]/page.tsx
interface PageProps {
  params: { id: string }
}

export default async function PatientDetailPage({ params }: PageProps) {
  const patient = await getPatient(params.id)
  
  if (!patient) {
    notFound()
  }
  
  return <PatientDetail patient={patient} />
}
```

### 3.4 Layout Pattern

```typescript
// app/(dashboard)/layout.tsx
import { Sidebar } from "@/components/sidebar/sidebar"

export default function DashboardLayout({
  children
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>
    </div>
  )
}
```

---

## 4. Component Patterns

### 4.1 Server vs Client Components

```typescript
// ✅ Server Component (default) - for data fetching
// components/patients/patient-list.tsx
import { getPatients } from "@/lib/api/patients"

export async function PatientList() {
  const patients = await getPatients()
  return (
    <ul>
      {patients.map(patient => (
        <PatientCard key={patient.id} patient={patient} />
      ))}
    </ul>
  )
}

// ✅ Client Component - for interactivity
// components/patients/patient-search.tsx
"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"

export function PatientSearch() {
  const [query, setQuery] = useState("")
  
  return (
    <Input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="Tìm kiếm bệnh nhân..."
    />
  )
}
```

### 4.2 Component Structure

```typescript
// components/patients/patient-card.tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils/format"
import type { Patient } from "@/types/patient"

interface PatientCardProps {
  patient: Patient
  onSelect?: (patient: Patient) => void
}

export function PatientCard({ patient, onSelect }: PatientCardProps) {
  return (
    <Card 
      className="cursor-pointer hover:bg-accent transition-colors"
      onClick={() => onSelect?.(patient)}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{patient.full_name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>{formatDate(patient.date_of_birth)}</span>
          <Badge variant="outline">{patient.gender}</Badge>
        </div>
        {patient.primary_diagnosis && (
          <Badge className="mt-2">{patient.primary_diagnosis}</Badge>
        )}
      </CardContent>
    </Card>
  )
}
```

### 4.3 Composition Pattern

Build complex UIs by composing smaller components:

```typescript
// Good: Composable components
<Card>
  <CardHeader>
    <CardTitle>Vital Signs</CardTitle>
    <CardDescription>Latest measurements</CardDescription>
  </CardHeader>
  <CardContent>
    <VitalSignsGrid data={vitals} />
  </CardContent>
  <CardFooter>
    <Button>Update</Button>
  </CardFooter>
</Card>
```

---

## 5. State Management

### 5.1 Server State with TanStack Query

```typescript
// lib/hooks/use-patients.ts
"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getPatients, createPatient, updatePatient } from "@/lib/api/patients"
import type { Patient, PatientCreate } from "@/types/patient"

export function usePatients() {
  return useQuery({
    queryKey: ["patients"],
    queryFn: getPatients
  })
}

export function usePatient(id: string) {
  return useQuery({
    queryKey: ["patients", id],
    queryFn: () => getPatient(id),
    enabled: !!id
  })
}

export function useCreatePatient() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: PatientCreate) => createPatient(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] })
    }
  })
}
```

### 5.2 Client State with Context

```typescript
// contexts/auth-context.tsx
"use client"

import { createContext, useContext, useState, useEffect } from "react"
import type { User } from "@/types/user"

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (phone: string, otp: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  // ... implementation
  
  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
```

---

## 6. API Integration

### 6.1 API Client Setup

```typescript
// lib/api/client.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers
    }
  })
  
  const json: ApiResponse<T> = await response.json()
  
  if (!json.success) {
    throw new Error(json.error?.message || "API Error")
  }
  
  return json.data as T
}
```

### 6.2 API Functions

```typescript
// lib/api/patients.ts
import { apiClient } from "./client"
import type { Patient, PatientCreate, PatientUpdate } from "@/types/patient"

export async function getPatients(): Promise<Patient[]> {
  return apiClient<Patient[]>("/api/v1/patients")
}

export async function getPatient(id: string): Promise<Patient> {
  return apiClient<Patient>(`/api/v1/patients/${id}`)
}

export async function createPatient(data: PatientCreate): Promise<Patient> {
  return apiClient<Patient>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify(data)
  })
}
```

### 6.3 Server Actions (Alternative)

```typescript
// app/actions/patients.ts
"use server"

import { revalidatePath } from "next/cache"
import { createPatient as createPatientAPI } from "@/lib/api/patients"

export async function createPatientAction(formData: FormData) {
  const data = {
    full_name: formData.get("full_name") as string,
    date_of_birth: formData.get("date_of_birth") as string,
    // ... other fields
  }
  
  await createPatientAPI(data)
  revalidatePath("/patients")
}
```

---

## 7. Styling Guidelines

### 7.1 Tailwind CSS Conventions

```typescript
// ✅ Good: Utility-first with consistent spacing
<div className="flex flex-col gap-4 p-6">
  <h1 className="text-2xl font-bold tracking-tight">Title</h1>
  <p className="text-muted-foreground">Description</p>
</div>

// ✅ Good: Using cn() for conditional classes
import { cn } from "@/lib/utils/cn"

<button className={cn(
  "px-4 py-2 rounded-md font-medium",
  variant === "primary" && "bg-primary text-primary-foreground",
  variant === "outline" && "border border-input bg-background",
  disabled && "opacity-50 cursor-not-allowed"
)}>
  Click me
</button>

// ❌ Bad: Inline styles, arbitrary values
<div style={{ padding: "27px" }}>
<div className="p-[27px]">
```

### 7.2 Design Tokens (via Shadcn)

Use semantic color tokens:

```typescript
// ✅ Good: Semantic tokens
"bg-background"      // White/dark based on theme
"text-foreground"    // Primary text color
"text-muted-foreground"  // Secondary text
"bg-primary"         // Primary brand color
"bg-destructive"     // Error/danger color
"border-input"       // Input border color
"bg-accent"          // Hover/active states

// ❌ Bad: Raw colors
"bg-white"
"text-gray-500"
"border-gray-300"
```

### 7.3 Responsive Design

```typescript
// Mobile-first approach
<div className="
  grid 
  grid-cols-1 
  gap-4
  md:grid-cols-2 
  lg:grid-cols-3 
  xl:grid-cols-4
">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>
```

---

## 8. Accessibility

### 8.1 Semantic HTML

```typescript
// ✅ Good: Semantic elements
<main>
  <article>
    <header>
      <h1>Patient Profile</h1>
    </header>
    <section aria-labelledby="vital-signs">
      <h2 id="vital-signs">Vital Signs</h2>
      {/* content */}
    </section>
  </article>
</main>

// ❌ Bad: Div soup
<div>
  <div>
    <div>Patient Profile</div>
  </div>
</div>
```

### 8.2 Accessible Forms

```typescript
<form>
  <div className="space-y-4">
    <div>
      <Label htmlFor="full_name">Họ và tên</Label>
      <Input 
        id="full_name"
        aria-describedby="name-error"
        aria-invalid={!!errors.full_name}
      />
      {errors.full_name && (
        <p id="name-error" className="text-sm text-destructive">
          {errors.full_name.message}
        </p>
      )}
    </div>
  </div>
</form>
```

### 8.3 Keyboard Navigation

- All interactive elements must be focusable
- Use `tabIndex={0}` sparingly
- Implement keyboard handlers for custom components

---

## 9. Testing Standards

### 9.1 Component Tests

```typescript
// components/patients/__tests__/patient-card.test.tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { PatientCard } from "../patient-card"

const mockPatient = {
  id: "1",
  full_name: "Nguyễn Văn A",
  date_of_birth: "1990-01-15",
  gender: "male",
  primary_diagnosis: "E11"
}

describe("PatientCard", () => {
  it("displays patient name", () => {
    render(<PatientCard patient={mockPatient} />)
    expect(screen.getByText("Nguyễn Văn A")).toBeInTheDocument()
  })
  
  it("calls onSelect when clicked", async () => {
    const onSelect = jest.fn()
    render(<PatientCard patient={mockPatient} onSelect={onSelect} />)
    
    await userEvent.click(screen.getByRole("article"))
    expect(onSelect).toHaveBeenCalledWith(mockPatient)
  })
})
```

### 9.2 Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific file
npm test -- patient-card.test.tsx

# Watch mode
npm test -- --watch
```

---

## 10. Performance Optimization

### 10.1 Image Optimization

```typescript
import Image from "next/image"

// ✅ Good: Next.js Image component
<Image
  src="/images/medical-scan.jpg"
  alt="X-ray scan"
  width={800}
  height={600}
  priority={false}
  placeholder="blur"
/>
```

### 10.2 Code Splitting

```typescript
// Dynamic imports for heavy components
import dynamic from "next/dynamic"

const MedicalImageViewer = dynamic(
  () => import("@/components/medical/medical-image-viewer"),
  { 
    loading: () => <Skeleton className="h-[400px]" />,
    ssr: false  // Disable SSR for client-only components
  }
)
```

### 10.3 Memoization

```typescript
"use client"

import { memo, useMemo, useCallback } from "react"

// Memoize expensive components
export const PatientList = memo(function PatientList({ patients }) {
  // Component implementation
})

// Memoize expensive calculations
const sortedPatients = useMemo(
  () => patients.sort((a, b) => a.name.localeCompare(b.name)),
  [patients]
)

// Memoize callbacks
const handleSelect = useCallback((patient: Patient) => {
  setSelectedPatient(patient)
}, [])
```

---

## Quick Reference

### Common Commands

```bash
# Start development server
cd frontend
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm test

# Add Shadcn component
npx shadcn-ui@latest add button
```

### File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | kebab-case | `patient-card.tsx` |
| Pages | lowercase folder | `app/patients/page.tsx` |
| Hooks | camelCase with use- | `use-patients.ts` |
| Types | PascalCase | `Patient`, `Doctor` |
| Utils | camelCase | `formatDate.ts` |

### Vietnamese UI Text

Always use Vietnamese for user-facing text:

```typescript
// ✅ Good
<Button>Lưu thay đổi</Button>
<Label>Họ và tên</Label>
placeholder="Nhập số điện thoại..."

// Code comments and variable names stay in English
```

---

> **Note for AI Agents**: When adding new features, check existing components in `components/ui/` first. Use Shadcn components as base. Follow Server Component patterns unless interactivity is needed.
