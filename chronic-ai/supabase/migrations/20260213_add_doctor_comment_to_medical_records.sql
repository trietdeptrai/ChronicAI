-- Add dedicated doctor comment field for medical records CRUD flow.
ALTER TABLE medical_records
ADD COLUMN IF NOT EXISTS doctor_comment TEXT;
