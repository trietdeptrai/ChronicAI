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
    ('11111111-1111-4111-a111-111111111111', NOW(), 136, 85, 73, 7.0, 'fasting', 98, 65.0, 'self_reported')
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
