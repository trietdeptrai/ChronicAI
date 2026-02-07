-- Seed Demo Data for ChronicAI
-- Run this in Supabase SQL Editor after setup_db.sql and setup_vector_search.sql
-- These UUIDs match the frontend demo users

-- ============================================
-- DEMO USERS
-- ============================================

-- Demo Patient User
INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '11111111-1111-4111-a111-111111111111',
    '+84901234567',
    'patient.demo@chronicai.vn',
    'patient',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

-- Demo Doctor User
INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '22222222-2222-4222-a222-222222222222',
    '+84909876543',
    'doctor.demo@chronicai.vn',
    'doctor',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

-- Additional Demo Patient Users
INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '11111111-1111-4111-a111-111111111112',
    '+84901234568',
    'patient.lan@chronicai.vn',
    'patient',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '11111111-1111-4111-a111-111111111113',
    '+84901234569',
    'patient.minh@chronicai.vn',
    'patient',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '11111111-1111-4111-a111-111111111114',
    '+84901234570',
    'patient.hoa@chronicai.vn',
    'patient',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, phone_number, email, role, is_active, is_verified)
VALUES (
    '11111111-1111-4111-a111-111111111115',
    '+84901234571',
    'patient.quang@chronicai.vn',
    'patient',
    true,
    true
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- DEMO HEALTHCARE FACILITY
-- ============================================

INSERT INTO healthcare_facilities (id, name, type, address, ward, district, province, phone, emergency_available)
VALUES (
    '33333333-3333-4333-a333-333333333333',
    'Trung tâm Y tế Quận 1',
    'district_hospital',
    '123 Nguyễn Huệ',
    'Bến Nghé',
    'Quận 1',
    'TP. Hồ Chí Minh',
    '+84283821234',
    true
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- DEMO DOCTOR PROFILE
-- ============================================

INSERT INTO doctors (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, medical_license_number, license_issue_date,
    medical_degree, graduation_year, medical_school, primary_specialty,
    years_of_experience, healthcare_facility_id, healthcare_facility_name,
    facility_type, position_title, department, verification_status,
    chronic_disease_focus, teleconsultation_enabled, profile_status
)
VALUES (
    '44444444-4444-4444-a444-444444444444',
    '22222222-2222-4222-a222-222222222222',
    'BS. Nguyễn Văn An',
    '1980-05-15',
    'male',
    '079080012345',
    '+84909876543',
    'doctor.demo@chronicai.vn',
    'VN-HCM-2010-12345',
    '2010-06-01',
    'Bác sĩ Chuyên khoa II',
    2005,
    'Đại học Y Dược TP.HCM',
    'Nội tiết - Đái tháo đường',
    18,
    '33333333-3333-4333-a333-333333333333',
    'Trung tâm Y tế Quận 1',
    'district_hospital',
    'Trưởng khoa Nội',
    'Khoa Nội',
    'verified',
    ARRAY['Đái tháo đường', 'Tăng huyết áp', 'Rối loạn mỡ máu'],
    true,
    'active'
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- DEMO PATIENT PROFILE
-- ============================================

INSERT INTO patients (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, address_street, address_ward, address_district, address_province,
    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
    blood_type, height_cm, weight_kg, bmi,
    chronic_conditions, primary_diagnosis, diagnosis_date, disease_stage,
    current_medications, medication_adherence_score, allergies,
    smoking_status, alcohol_consumption, exercise_frequency,
    insurance_provider, insurance_number, insurance_expiry, insurance_coverage_level,
    assigned_doctor_id, triage_priority, profile_status, last_checkup_date
)
VALUES (
    '11111111-1111-4111-a111-111111111111',
    '11111111-1111-4111-a111-111111111111',
    'Trần Thị Bình',
    '1965-03-20',
    'female',
    '079065054321',
    '+84901234567',
    'patient.demo@chronicai.vn',
    '456 Lê Lợi',
    'Phường Bến Thành',
    'Quận 1',
    'TP. Hồ Chí Minh',
    'Trần Văn Cường',
    '+84901111222',
    'Con trai',
    'A+',
    158,
    65,
    26.0,
    '[{"icd10_code": "E11", "name": "Đái tháo đường type 2", "diagnosed_date": "2018-06-15", "stage": "controlled", "notes": "Kiểm soát tốt với thuốc"}, {"icd10_code": "I10", "name": "Tăng huyết áp", "diagnosed_date": "2019-02-10", "stage": "stage_1", "notes": "Huyết áp dao động 130-145/85-95"}]',
    'E11',
    '2018-06-15',
    'controlled',
    '[{"name": "Metformin", "dosage": "500mg", "frequency": "2 lần/ngày", "timing": "Sau ăn sáng và tối", "prescriber": "BS. Nguyễn Văn An", "start_date": "2018-06-20"}, {"name": "Amlodipine", "dosage": "5mg", "frequency": "1 lần/ngày", "timing": "Sáng", "prescriber": "BS. Nguyễn Văn An", "start_date": "2019-02-15"}]',
    8,
    ARRAY['Penicillin', 'Sulfonamide'],
    'never',
    'none',
    'light',
    'BHYT',
    'DN4790650543210001',
    '2025-12-31',
    'level_1',
    '44444444-4444-4444-a444-444444444444',
    'medium',
    'active',
    '2025-01-05'
) ON CONFLICT (id) DO NOTHING;

-- Additional Demo Patient Profiles
INSERT INTO patients (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, address_street, address_ward, address_district, address_province,
    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
    blood_type, height_cm, weight_kg, bmi,
    chronic_conditions, primary_diagnosis, diagnosis_date, disease_stage,
    current_medications, medication_adherence_score, allergies,
    smoking_status, alcohol_consumption, exercise_frequency,
    insurance_provider, insurance_number, insurance_expiry, insurance_coverage_level,
    assigned_doctor_id, triage_priority, profile_status, last_checkup_date
)
VALUES (
    '11111111-1111-4111-a111-111111111112',
    '11111111-1111-4111-a111-111111111112',
    'Nguyễn Thị Lan',
    '1972-09-11',
    'female',
    '079072091111',
    '+84901234568',
    'patient.lan@chronicai.vn',
    '12 Trần Hưng Đạo',
    'Phường Cầu Ông Lãnh',
    'Quận 1',
    'TP. Hồ Chí Minh',
    'Nguyễn Văn Hùng',
    '+84903334455',
    'Chồng',
    'O+',
    160,
    72,
    28.1,
    '[{"icd10_code": "I10", "name": "Tăng huyết áp", "diagnosed_date": "2016-04-01", "stage": "stage_2", "notes": "Huyết áp thường 150-165/90-100"}, {"icd10_code": "E78.5", "name": "Rối loạn lipid máu", "diagnosed_date": "2020-08-10", "stage": "moderate", "notes": "LDL cao"}]',
    'I10',
    '2016-04-01',
    'stage_2',
    '[{"name": "Losartan", "dosage": "50mg", "frequency": "1 lần/ngày", "timing": "Sáng", "prescriber": "BS. Nguyễn Văn An", "start_date": "2016-04-05"}, {"name": "Atorvastatin", "dosage": "20mg", "frequency": "1 lần/ngày", "timing": "Tối", "prescriber": "BS. Nguyễn Văn An", "start_date": "2020-08-15"}]',
    6,
    ARRAY['NSAIDs'],
    'never',
    'occasional',
    'light',
    'BHYT',
    'DN4790720911110002',
    '2026-12-31',
    'level_2',
    '44444444-4444-4444-a444-444444444444',
    'high',
    'active',
    '2025-01-12'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO patients (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, address_street, address_ward, address_district, address_province,
    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
    blood_type, height_cm, weight_kg, bmi,
    chronic_conditions, primary_diagnosis, diagnosis_date, disease_stage,
    current_medications, medication_adherence_score, allergies,
    smoking_status, alcohol_consumption, exercise_frequency,
    insurance_provider, insurance_number, insurance_expiry, insurance_coverage_level,
    assigned_doctor_id, triage_priority, profile_status, last_checkup_date
)
VALUES (
    '11111111-1111-4111-a111-111111111113',
    '11111111-1111-4111-a111-111111111113',
    'Lê Văn Minh',
    '1958-01-28',
    'male',
    '079058012222',
    '+84901234569',
    'patient.minh@chronicai.vn',
    '88 Nguyễn Huệ',
    'Phường Bến Nghé',
    'Quận 1',
    'TP. Hồ Chí Minh',
    'Lê Thị Thảo',
    '+84906667788',
    'Vợ',
    'A-',
    168,
    70,
    24.8,
    '[{"icd10_code": "I50.9", "name": "Suy tim", "diagnosed_date": "2023-11-02", "stage": "decompensated_risk", "notes": "Khó thở khi gắng sức, phù chân nhẹ"}, {"icd10_code": "I25.10", "name": "Bệnh mạch vành", "diagnosed_date": "2022-05-20", "stage": "stable", "notes": "Đau thắt ngực ổn định"}]',
    'I50.9',
    '2023-11-02',
    'decompensated_risk',
    '[{"name": "Furosemide", "dosage": "20mg", "frequency": "1 lần/ngày", "timing": "Sáng", "prescriber": "BS. Nguyễn Văn An", "start_date": "2023-11-05"}, {"name": "Bisoprolol", "dosage": "2.5mg", "frequency": "1 lần/ngày", "timing": "Sáng", "prescriber": "BS. Nguyễn Văn An", "start_date": "2022-06-01"}, {"name": "Aspirin", "dosage": "81mg", "frequency": "1 lần/ngày", "timing": "Sau ăn", "prescriber": "BS. Nguyễn Văn An", "start_date": "2022-05-25"}]',
    7,
    ARRAY['None'],
    'former',
    'none',
    'none',
    'BHYT',
    'DN4790580122220003',
    '2026-06-30',
    'level_1',
    '44444444-4444-4444-a444-444444444444',
    'urgent',
    'active',
    '2025-01-03'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO patients (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, address_street, address_ward, address_district, address_province,
    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
    blood_type, height_cm, weight_kg, bmi,
    chronic_conditions, primary_diagnosis, diagnosis_date, disease_stage,
    current_medications, medication_adherence_score, allergies,
    smoking_status, alcohol_consumption, exercise_frequency,
    insurance_provider, insurance_number, insurance_expiry, insurance_coverage_level,
    assigned_doctor_id, triage_priority, profile_status, last_checkup_date
)
VALUES (
    '11111111-1111-4111-a111-111111111114',
    '11111111-1111-4111-a111-111111111114',
    'Phạm Thị Hoa',
    '1969-07-04',
    'female',
    '079069073333',
    '+84901234570',
    'patient.hoa@chronicai.vn',
    '31 Cách Mạng Tháng 8',
    'Phường Phạm Ngũ Lão',
    'Quận 1',
    'TP. Hồ Chí Minh',
    'Phạm Văn Nam',
    '+84909990001',
    'Con trai',
    'B+',
    155,
    58,
    24.1,
    '[{"icd10_code": "N18.3", "name": "Bệnh thận mạn (CKD độ 3)", "diagnosed_date": "2021-09-15", "stage": "stage_3", "notes": "eGFR ~45-55"}, {"icd10_code": "E11", "name": "Đái tháo đường type 2", "diagnosed_date": "2017-02-01", "stage": "suboptimal", "notes": "HbA1c khoảng 7.8%"}]',
    'N18.3',
    '2021-09-15',
    'stage_3',
    '[{"name": "Metformin", "dosage": "500mg", "frequency": "2 lần/ngày", "timing": "Sau ăn", "prescriber": "BS. Nguyễn Văn An", "start_date": "2017-02-10"}, {"name": "Dapagliflozin", "dosage": "10mg", "frequency": "1 lần/ngày", "timing": "Sáng", "prescriber": "BS. Nguyễn Văn An", "start_date": "2022-03-20"}]',
    5,
    ARRAY['Sulfonamide'],
    'never',
    'none',
    'light',
    'BHYT',
    'DN4790690733330004',
    '2026-12-31',
    'level_3',
    '44444444-4444-4444-a444-444444444444',
    'medium',
    'active',
    '2024-12-20'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO patients (
    id, user_id, full_name, date_of_birth, gender, national_id,
    phone_primary, email, address_street, address_ward, address_district, address_province,
    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
    blood_type, height_cm, weight_kg, bmi,
    chronic_conditions, primary_diagnosis, diagnosis_date, disease_stage,
    current_medications, medication_adherence_score, allergies,
    smoking_status, alcohol_consumption, exercise_frequency,
    insurance_provider, insurance_number, insurance_expiry, insurance_coverage_level,
    assigned_doctor_id, triage_priority, profile_status, last_checkup_date
)
VALUES (
    '11111111-1111-4111-a111-111111111115',
    '11111111-1111-4111-a111-111111111115',
    'Đỗ Quốc Quang',
    '1985-12-09',
    'male',
    '079085124444',
    '+84901234571',
    'patient.quang@chronicai.vn',
    '77 Điện Biên Phủ',
    'Phường Đa Kao',
    'Quận 1',
    'TP. Hồ Chí Minh',
    'Đỗ Thị Mai',
    '+84908887766',
    'Vợ',
    'unknown',
    172,
    79,
    26.7,
    '[{"icd10_code": "R73.03", "name": "Tiền đái tháo đường", "diagnosed_date": "2024-06-10", "stage": "at_risk", "notes": "Đường huyết lúc đói 6.1-6.4"}, {"icd10_code": "E66.3", "name": "Thừa cân", "diagnosed_date": "2020-01-01", "stage": "mild", "notes": "BMI ~27"}]',
    'R73.03',
    '2024-06-10',
    'at_risk',
    '[{"name": "Lifestyle modification", "dosage": "N/A", "frequency": "Hàng ngày", "timing": "N/A", "prescriber": "BS. Nguyễn Văn An", "start_date": "2024-06-15"}]',
    8,
    ARRAY[]::TEXT[],
    'never',
    'occasional',
    'moderate',
    'BHYT',
    'DN4790851244440005',
    '2027-12-31',
    'level_1',
    '44444444-4444-4444-a444-444444444444',
    'low',
    'active',
    '2025-01-20'
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- DEMO VITAL SIGNS (Last 7 days)
-- ============================================

INSERT INTO vital_signs (patient_id, recorded_at, blood_pressure_systolic, blood_pressure_diastolic, heart_rate, blood_glucose, blood_glucose_timing, oxygen_saturation, weight_kg, source)
VALUES
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '6 days', 142, 92, 78, 7.8, 'fasting', 97, 65.2, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '5 days', 138, 88, 75, 8.2, 'after_meal', 98, 65.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '4 days', 145, 94, 80, 7.5, 'fasting', 97, 65.3, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '3 days', 135, 86, 72, 9.1, 'after_meal', 98, 64.8, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '2 days', 140, 90, 76, 7.2, 'fasting', 97, 65.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW() - INTERVAL '1 day', 138, 88, 74, 8.5, 'after_meal', 98, 65.1, 'self_reported'),
    ('11111111-1111-4111-a111-111111111111', NOW(), 136, 85, 73, 7.0, 'fasting', 98, 65.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111112', NOW() - INTERVAL '3 days', 162, 98, 82, 6.2, 'fasting', 97, 72.1, 'self_reported'),
    ('11111111-1111-4111-a111-111111111112', NOW() - INTERVAL '1 day', 158, 96, 80, 6.5, 'random', 98, 71.8, 'self_reported'),
    ('11111111-1111-4111-a111-111111111112', NOW(), 155, 95, 78, 6.1, 'fasting', 98, 71.9, 'self_reported'),
    ('11111111-1111-4111-a111-111111111113', NOW() - INTERVAL '2 days', 148, 90, 96, 6.8, 'random', 93, 70.5, 'self_reported'),
    ('11111111-1111-4111-a111-111111111113', NOW() - INTERVAL '1 day', 150, 92, 102, 6.9, 'random', 92, 70.8, 'self_reported'),
    ('11111111-1111-4111-a111-111111111113', NOW(), 152, 94, 104, 7.1, 'random', 91, 71.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111114', NOW() - INTERVAL '3 days', 132, 82, 76, 9.4, 'after_meal', 98, 58.2, 'self_reported'),
    ('11111111-1111-4111-a111-111111111114', NOW() - INTERVAL '1 day', 130, 80, 74, 8.8, 'after_meal', 98, 58.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111114', NOW(), 128, 78, 72, 7.6, 'fasting', 98, 57.9, 'self_reported'),
    ('11111111-1111-4111-a111-111111111115', NOW() - INTERVAL '2 days', 128, 82, 70, 6.3, 'fasting', 98, 79.0, 'self_reported'),
    ('11111111-1111-4111-a111-111111111115', NOW() - INTERVAL '1 day', 126, 80, 69, 7.9, 'after_meal', 98, 78.7, 'self_reported'),
    ('11111111-1111-4111-a111-111111111115', NOW(), 125, 78, 68, 6.2, 'fasting', 98, 78.8, 'self_reported')
ON CONFLICT DO NOTHING;

-- ============================================
-- DEMO MEDICAL RECORDS
-- ============================================

INSERT INTO medical_records (id, patient_id, doctor_id, record_type, title, content_text, is_verified, verified_by, verified_at)
VALUES
    (
        '55555555-5555-4555-a555-555555555551',
        '11111111-1111-4111-a111-111111111111',
        '44444444-4444-4444-a444-444444444444',
        'prescription',
        'Đơn thuốc tháng 1/2025',
        'Chẩn đoán: Đái tháo đường type 2, Tăng huyết áp giai đoạn 1.

Thuốc kê đơn:
1. Metformin 500mg - Uống 2 viên/ngày (sáng, tối) sau ăn
2. Amlodipine 5mg - Uống 1 viên/ngày vào buổi sáng
3. Aspirin 81mg - Uống 1 viên/ngày sau ăn trưa

Lưu ý:
- Kiểm tra đường huyết lúc đói mỗi sáng
- Đo huyết áp 2 lần/ngày (sáng, tối)
- Tái khám sau 1 tháng
- Liên hệ ngay nếu có triệu chứng bất thường',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '30 days'
    ),
    (
        '55555555-5555-4555-a555-555555555552',
        '11111111-1111-4111-a111-111111111111',
        '44444444-4444-4444-a444-444444444444',
        'lab',
        'Xét nghiệm máu định kỳ Q4/2024',
        'KẾT QUẢ XÉT NGHIỆM MÁU

Ngày xét nghiệm: 15/12/2024
Phòng xét nghiệm: Trung tâm Y tế Quận 1

1. Đường huyết lúc đói: 7.2 mmol/L (Bình thường: 3.9-6.1)
   → Cao hơn bình thường, cần theo dõi

2. HbA1c: 7.1% (Mục tiêu: <7%)
   → Kiểm soát tốt, duy trì chế độ điều trị

3. Cholesterol toàn phần: 5.8 mmol/L (Bình thường: <5.2)
   → Tăng nhẹ, cần chú ý chế độ ăn

4. LDL Cholesterol: 3.5 mmol/L (Mục tiêu: <2.6)
   → Cao, xem xét bổ sung statin

5. HDL Cholesterol: 1.4 mmol/L (Bình thường: >1.0)
   → Bình thường

6. Triglyceride: 2.1 mmol/L (Bình thường: <1.7)
   → Tăng nhẹ

7. Creatinine: 85 µmol/L (Bình thường: 45-90)
   → Bình thường, chức năng thận ổn

8. eGFR: 72 mL/min/1.73m²
   → Suy thận mức độ 2 (nhẹ)

KẾT LUẬN: Kiểm soát đường huyết tốt, cần cải thiện mỡ máu qua chế độ ăn và vận động.',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '45 days'
    ),
    (
        '55555555-5555-4555-a555-555555555553',
        '11111111-1111-4111-a111-111111111111',
        '44444444-4444-4444-a444-444444444444',
        'notes',
        'Ghi chú khám định kỳ 01/2025',
        'KHÁM ĐỊNH KỲ - BỆNH NHÂN ĐÁI THÁO ĐƯỜNG

Ngày khám: 05/01/2025
Bác sĩ: BS. Nguyễn Văn An

TÌNH TRẠNG HIỆN TẠI:
- Bệnh nhân ổn định, tuân thủ điều trị tốt
- Không có triệu chứng hạ đường huyết
- Huyết áp kiểm soát được với thuốc
- Đôi khi đau đầu nhẹ khi huyết áp tăng

KHÁM LÂM SÀNG:
- Huyết áp: 138/88 mmHg
- Mạch: 74 lần/phút
- Cân nặng: 65 kg (không thay đổi)
- BMI: 26.0 (thừa cân)
- Bàn chân: không có loét, cảm giác bình thường

ĐÁNH GIÁ:
1. Đái tháo đường type 2 kiểm soát tốt
2. Tăng huyết áp giai đoạn 1 - chưa đạt mục tiêu (<130/80)
3. Rối loạn mỡ máu - cần cải thiện

KẾ HOẠCH:
- Tiếp tục thuốc hiện tại
- Tăng cường vận động (đi bộ 30 phút/ngày)
- Chế độ ăn giảm mỡ, giảm muối
- Xem xét bổ sung Rosuvastatin nếu mỡ máu không cải thiện
- Tái khám sau 1 tháng',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '25 days'
    )
ON CONFLICT (id) DO NOTHING;

-- Additional Demo Medical Records (one note per extra patient)
INSERT INTO medical_records (id, patient_id, doctor_id, record_type, title, content_text, is_verified, verified_by, verified_at)
VALUES
    (
        '55555555-5555-4555-a555-555555555554',
        '11111111-1111-4111-a111-111111111112',
        '44444444-4444-4444-a444-444444444444',
        'notes',
        'Ghi chú tăng huyết áp 01/2025',
        'Bệnh nhân tăng huyết áp mức độ 2, cần theo dõi HA tại nhà 2 lần/ngày.\nMục tiêu < 130/80 nếu dung nạp.\nNhắc tuân thủ thuốc và giảm muối.',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '20 days'
    ),
    (
        '55555555-5555-4555-a555-555555555555',
        '11111111-1111-4111-a111-111111111113',
        '44444444-4444-4444-a444-444444444444',
        'notes',
        'Ghi chú suy tim 01/2025',
        'Bệnh nhân có nguy cơ mất bù suy tim.\nDặn theo dõi cân nặng mỗi sáng, phù chân, khó thở.\nNếu tăng cân >2kg/3 ngày hoặc SpO2 < 92% cần liên hệ ngay.',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '15 days'
    ),
    (
        '55555555-5555-4555-a555-555555555556',
        '11111111-1111-4111-a111-111111111114',
        '44444444-4444-4444-a444-444444444444',
        'notes',
        'Ghi chú CKD + ĐTĐ 12/2024',
        'Bệnh thận mạn độ 3.\nƯu tiên kiểm soát đường huyết và HA.\nKhuyến nghị xét nghiệm creatinine/eGFR định kỳ và điều chỉnh thuốc theo chức năng thận.',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '35 days'
    ),
    (
        '55555555-5555-4555-a555-555555555557',
        '11111111-1111-4111-a111-111111111115',
        '44444444-4444-4444-a444-444444444444',
        'notes',
        'Ghi chú tiền đái tháo đường 01/2025',
        'Tiền đái tháo đường.\nKhuyến nghị giảm 5-7% cân nặng, vận động 150 phút/tuần.\nTheo dõi đường huyết lúc đói và HbA1c mỗi 3-6 tháng.',
        true,
        '44444444-4444-4444-a444-444444444444',
        NOW() - INTERVAL '10 days'
    )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- DEMO DOCTOR-PATIENT ASSIGNMENT
-- ============================================

INSERT INTO doctor_patient_assignments (doctor_id, patient_id, relationship_type, assigned_date, status)
VALUES (
    '44444444-4444-4444-a444-444444444444',
    '11111111-1111-4111-a111-111111111111',
    'primary_care',
    '2018-06-20',
    'active'
) ON CONFLICT (doctor_id, patient_id) DO NOTHING;

-- Additional Demo Assignments
INSERT INTO doctor_patient_assignments (doctor_id, patient_id, relationship_type, assigned_date, status)
VALUES
    ('44444444-4444-4444-a444-444444444444', '11111111-1111-4111-a111-111111111112', 'primary_care', '2020-08-15', 'active'),
    ('44444444-4444-4444-a444-444444444444', '11111111-1111-4111-a111-111111111113', 'primary_care', '2023-11-05', 'active'),
    ('44444444-4444-4444-a444-444444444444', '11111111-1111-4111-a111-111111111114', 'primary_care', '2021-09-20', 'active'),
    ('44444444-4444-4444-a444-444444444444', '11111111-1111-4111-a111-111111111115', 'primary_care', '2024-06-15', 'active')
ON CONFLICT (doctor_id, patient_id) DO NOTHING;

-- ============================================
-- DEMO CONSULTATION HISTORY
-- ============================================

INSERT INTO consultations (id, patient_id, doctor_id, chief_complaint, status, priority, started_at, ended_at, messages)
VALUES (
    '66666666-6666-4666-a666-666666666666',
    '11111111-1111-4111-a111-111111111111',
    '44444444-4444-4444-a444-444444444444',
    'Hỏi về huyết áp cao',
    'resolved',
    'medium',
    NOW() - INTERVAL '7 days',
    NOW() - INTERVAL '7 days' + INTERVAL '30 minutes',
    '[{"role": "user", "content": "Huyết áp của tôi cao quá, 150/95, tôi nên làm gì?", "timestamp": "2025-01-23T10:00:00Z"}, {"role": "assistant", "content": "Huyết áp 150/95 mmHg thuộc mức tăng huyết áp độ 1. Bạn nên: 1) Nghỉ ngơi 10-15 phút rồi đo lại, 2) Uống thuốc huyết áp đúng giờ, 3) Giảm muối trong bữa ăn, 4) Nếu vẫn cao trên 160/100 sau 1 giờ, hãy liên hệ bác sĩ.", "timestamp": "2025-01-23T10:01:00Z"}]'
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Demo data seeded successfully!' AS status;
