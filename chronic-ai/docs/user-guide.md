# ChronicAI User Guide

## Table of Contents
1. Introduction
2. Access and Role Selection
3. Navigation Overview
4. Doctor Workflows
5. Patient Workflows
6. Appointments Workflow
7. AI Features
8. Data Import/Export
9. Troubleshooting
10. Support and Next Steps

## 1. Introduction

ChronicAI is a chronic disease management application with two user roles:
- Doctor: manage patient profiles, records, vitals, appointments, and AI-assisted analysis.
- Patient: review personal health information, chat with AI, and request appointments.

This guide covers the current application behavior in `frontend/app` as implemented in this repository.

## 2. Access and Role Selection

1. Open the app in your browser (default local URL: `http://localhost:3000`).
2. On the landing page, select a role:
- `Doctor`
- `Patient`
3. You are redirected to `/dashboard` with role-specific features.

Notes:
- The current auth context is demo-oriented and stores the selected role in browser local storage.
- Use logout in the sidebar to return to role selection.

## 3. Navigation Overview

Sidebar items:
- Dashboard (`/dashboard`)
- Patients (`/dashboard/patients`) - doctor only
- Calendar (`/dashboard/calendar`)
- AI Chat (`/dashboard/chat`)
- Settings (`/dashboard/settings`)
- Logout

## 4. Doctor Workflows

### 4.1 Dashboard

Use the doctor dashboard to:
- Monitor key stats: total patients, urgent/high-priority cases, pending consults, alerts.
- Search/select patients.
- Review latest record, vitals, chronic conditions, and quick summary cards.
- Open full profile from `Open full profile`.

### 4.2 Manage Patient Profiles

Go to `Patients` page to:
- Search and filter by triage priority.
- Create patient profiles (`New Patient`).
- Edit or delete existing profiles.
- Import metadata from `.json`/`.pdf` into form fields (prefill only).
- Export metadata as `.json` or `.pdf`.

Required fields for create/update include name, date of birth, primary phone, address components, and emergency contact fields.

### 4.3 Patient Detail Page

From `/dashboard/patients/[patientId]`, doctors can:
- Update profile photo.
- Add/edit/delete vital signs (BP, heart rate, glucose, SpO2, temperature, weight, notes).
- Upload medical records/images (lab, X-ray, ECG, CT, MRI).
- Review AI-generated analysis for uploaded files.
- Add optional doctor comments after upload.
- Edit existing medical records (including replacement file).
- Delete medical records.
- Generate or regenerate AI clinical summary.

## 5. Patient Workflows

### 5.1 Patient Dashboard

Patient dashboard shows:
- Profile overview.
- Last checkup and latest record indicators.
- Recent vitals/record counts.

### 5.2 Patient AI Chat

On `AI Chat`, patients get patient-specific chat using their own patient ID context.
Use this for follow-up questions about symptoms, medications, and ongoing care guidance.

## 6. Appointments Workflow

### For Patients

In `Calendar`:
1. Select day/week view.
2. Click a time slot to open booking dialog.
3. Fill required fields (chief complaint/reason required).
4. Submit booking request.
5. View reminders for upcoming appointments.

### For Doctors

In `Calendar`:
1. Open pending appointment items.
2. Accept or reject requests.
3. Add doctor note and optional rejection reason.
4. Track statuses: pending, accepted, rejected, cancelled, completed.

## 7. AI Features

### 7.1 Doctor AI Chat

Doctors use the orchestrator chat interface to ask cross-patient or case-level questions without pre-selecting a patient in the chat page.

### 7.2 Imaging and ECG Analysis

After uploading clinical images/records:
- The system runs staged processing (validation, analysis, save).
- ECG flows include embedding/classifier stages.
- AI analysis appears in record detail cards.

### 7.3 Clinical Summary

On patient detail, doctors can generate an AI summary of clinical context and latest data for quick review.

## 8. Data Import/Export

### 8.1 Patient Metadata (Patients page)
- Export: metadata as JSON/PDF.
- Import: JSON/PDF to prefill create/edit form.

### 8.2 Full Patient Data (Patient detail)
- Export full record as ZIP (text + files).
- Export file attachments as ZIP.
- Import full record from ZIP.

## 9. Troubleshooting

### Cannot load patient list/dashboard data
- Check backend is running (`http://localhost:8000`).
- Confirm frontend `NEXT_PUBLIC_API_URL` points to backend.
- Confirm database and seed data are initialized.

### Upload fails
- Ensure file type is supported (image/PDF where applicable).
- Retry with smaller file size.
- Check backend logs for storage or model errors.

### Appointment actions fail
- Verify role context (`Doctor` vs `Patient`).
- Check network/API availability.

### Missing AI outputs
- Confirm AI provider credentials are set in backend environment.
- Check backend logs for model/auth/permission errors.

## 10. Support and Next Steps

For deployment/setup and environment configuration, refer to:
- Root setup guide: `README.md`
- API docs (when backend is running): `http://localhost:8000/docs`

