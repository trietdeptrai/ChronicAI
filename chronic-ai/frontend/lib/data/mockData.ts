// Mock data for chronic disease management system

export type DiseaseType = 'hypertension' | 'diabetes' | 'cardiovascular' | 'cancer' | 'asthma';

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'M' | 'F';
  diseases: DiseaseType[];
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  lastVisit: string;
  nextFollowUp: string;
  avatar?: string;
}

export interface MedicalRecord {
  id: string;
  patientId: string;
  date: string;
  type: 'diagnosis' | 'lab' | 'imaging' | 'prescription' | 'visit' | 'emergency';
  title: string;
  summary: string;
  details: {
    diagnoses?: string[];
    medications?: { name: string; dosage: string; frequency: string }[];
    labResults?: { test: string; value: string; normal: string; status: 'normal' | 'abnormal' }[];
    vitals?: { bp?: string; glucose?: string; hr?: number; temp?: number; weight?: number };
    findings?: string[];
    recommendations?: string[];
    imageUrl?: string;
  };
  uploadedBy: 'doctor' | 'system';
  alerts?: string[];
}

export interface Alert {
  id: string;
  patientId: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  date: string;
  read: boolean;
}

// Mock patients
export const mockPatients: Patient[] = [
  {
    id: 'p1',
    name: 'Nguyễn Văn An',
    age: 58,
    gender: 'M',
    diseases: ['hypertension', 'diabetes'],
    riskLevel: 'high',
    lastVisit: '2026-01-20',
    nextFollowUp: '2026-02-15',
  },
  {
    id: 'p2',
    name: 'Trần Thị Bình',
    age: 65,
    gender: 'F',
    diseases: ['cardiovascular', 'hypertension'],
    riskLevel: 'critical',
    lastVisit: '2026-01-25',
    nextFollowUp: '2026-02-01',
  },
  {
    id: 'p3',
    name: 'Lê Minh Cường',
    age: 42,
    gender: 'M',
    diseases: ['asthma'],
    riskLevel: 'medium',
    lastVisit: '2026-01-15',
    nextFollowUp: '2026-03-15',
  },
  {
    id: 'p4',
    name: 'Phạm Thị Dung',
    age: 71,
    gender: 'F',
    diseases: ['cancer', 'hypertension'],
    riskLevel: 'high',
    lastVisit: '2026-01-22',
    nextFollowUp: '2026-02-05',
  },
  {
    id: 'p5',
    name: 'Hoàng Văn Em',
    age: 55,
    gender: 'M',
    diseases: ['diabetes', 'cardiovascular'],
    riskLevel: 'high',
    lastVisit: '2026-01-18',
    nextFollowUp: '2026-02-18',
  },
];

// Mock medical records
export const mockRecords: MedicalRecord[] = [
  {
    id: 'r1',
    patientId: 'p1',
    date: '2026-01-20',
    type: 'visit',
    title: 'Khám định kỳ - Tháng 1/2026',
    summary: 'Huyết áp vẫn cao 160/95. Đường huyết lúc đói 145 mg/dL. Tăng liều thuốc hạ áp.',
    details: {
      diagnoses: ['Tăng huyết áp độ 2', 'Đái tháo đường type 2 chưa kiểm soát tốt'],
      vitals: {
        bp: '160/95 mmHg',
        glucose: '145 mg/dL',
        hr: 78,
        weight: 82,
      },
      medications: [
        { name: 'Amlodipine', dosage: '10mg', frequency: '1 lần/ngày' },
        { name: 'Metformin', dosage: '850mg', frequency: '2 lần/ngày' },
        { name: 'Losartan', dosage: '50mg', frequency: '1 lần/ngày' },
      ],
      recommendations: [
        'Tăng liều Amlodipine lên 10mg',
        'Tiếp tục kiểm soát chế độ ăn ít muối, ít đường',
        'Tập thể dục nhẹ 30 phút/ngày',
        'Tái khám sau 4 tuần',
      ],
    },
    uploadedBy: 'doctor',
    alerts: ['Huyết áp cao hơn mục tiêu (>140/90)', 'Đường huyết đói cao (mục tiêu <130)'],
  },
  {
    id: 'r2',
    patientId: 'p1',
    date: '2026-01-15',
    type: 'lab',
    title: 'Kết quả xét nghiệm định kỳ',
    summary: 'HbA1c 7.8%, Cholesterol tổng 245 mg/dL, LDL cao.',
    details: {
      labResults: [
        { test: 'HbA1c', value: '7.8%', normal: '<7%', status: 'abnormal' },
        { test: 'Glucose lúc đói', value: '145 mg/dL', normal: '70-100 mg/dL', status: 'abnormal' },
        { test: 'Cholesterol tổng', value: '245 mg/dL', normal: '<200 mg/dL', status: 'abnormal' },
        { test: 'LDL', value: '155 mg/dL', normal: '<100 mg/dL', status: 'abnormal' },
        { test: 'HDL', value: '42 mg/dL', normal: '>40 mg/dL', status: 'normal' },
        { test: 'Triglycerides', value: '185 mg/dL', normal: '<150 mg/dL', status: 'abnormal' },
        { test: 'Creatinine', value: '1.1 mg/dL', normal: '0.7-1.3 mg/dL', status: 'normal' },
      ],
      recommendations: [
        'Cần cân nhắc thêm thuốc hạ lipid máu (Statin)',
        'Kiểm soát đường huyết tốt hơn',
        'Chế độ ăn ít mỡ bão hòa',
      ],
    },
    uploadedBy: 'doctor',
    alerts: ['HbA1c cao - kiểm soát đái tháo đường chưa tốt', 'LDL cao - nguy cơ tim mạch'],
  },
  {
    id: 'r3',
    patientId: 'p2',
    date: '2026-01-25',
    type: 'imaging',
    title: 'Siêu âm tim',
    summary: 'EF 42%, phì đại thất trái, regurgitation van 2 lá nhẹ.',
    details: {
      findings: [
        'Phân suất tống máu (EF) giảm: 42% (bình thường >55%)',
        'Phì đại thất trái đồng tâm',
        'Hở van 2 lá độ 1/4',
        'Kích thước tâm nhĩ trái tăng nhẹ',
        'Chức năng tâm thu thất phải bình thường',
      ],
      recommendations: [
        'Chẩn đoán: Suy tim có triệu chứng, EF giảm (HFrEF)',
        'Cần bắt đầu điều trị suy tim: ACE-inhibitor/ARB, Beta-blocker',
        'Hạn chế muối <2g/ngày',
        'Theo dõi sát - tái khám sau 1 tuần',
      ],
      imageUrl: 'https://images.unsplash.com/photo-1559757175-0eb30cd8c063?w=600',
    },
    uploadedBy: 'doctor',
    alerts: ['EF giảm - suy tim cần can thiệp điều trị ngay'],
  },
  {
    id: 'r4',
    patientId: 'p2',
    date: '2026-01-25',
    type: 'visit',
    title: 'Khám cấp cứu - Khó thở',
    summary: 'Nhập viện do khó thở, phù 2 chân. Chẩn đoán suy tim cấp. BP 170/100.',
    details: {
      diagnoses: ['Suy tim cấp trên nền bệnh tim mạch mạn tính', 'Tăng huyết áp không kiểm soát'],
      vitals: {
        bp: '170/100 mmHg',
        hr: 105,
        temp: 36.8,
      },
      medications: [
        { name: 'Furosemide IV', dosage: '40mg', frequency: 'Stat' },
        { name: 'Nitroglycerin', dosage: 'theo pump', frequency: 'Tiếp diễn' },
        { name: 'Bisoprolol', dosage: '2.5mg', frequency: '1 lần/ngày' },
      ],
      recommendations: [
        'Nhập viện điều trị nội trú',
        'Theo dõi sát sinh hiệu',
        'Hạn chế dịch truyền',
        'Siêu âm tim đánh giá chức năng',
      ],
    },
    uploadedBy: 'doctor',
    alerts: ['Tình trạng cấp cứu', 'Huyết áp rất cao', 'Cần nhập viện'],
  },
  {
    id: 'r5',
    patientId: 'p3',
    date: '2026-01-15',
    type: 'prescription',
    title: 'Đơn thuốc điều trị hen suyễn',
    summary: 'Tăng liều thuốc kiểm soát do cơn hen tăng trong mùa lạnh.',
    details: {
      diagnoses: ['Hen phế quản kiểm soát một phần'],
      medications: [
        { name: 'Seretide 250 (Fluticasone/Salmeterol)', dosage: '250/25 mcg', frequency: '2 lần/ngày' },
        { name: 'Ventolin (Salbutamol)', dosage: '100 mcg', frequency: 'Khi cần (cấp cứu)' },
        { name: 'Montelukast', dosage: '10mg', frequency: '1 lần/ngày buổi tối' },
      ],
      recommendations: [
        'Sử dụng thuốc hít đúng kỹ thuật',
        'Tránh tiếp xúc khói bụi, không khí lạnh',
        'Tái khám nếu cơn hen >2 lần/tuần',
      ],
    },
    uploadedBy: 'doctor',
  },
  {
    id: 'r6',
    patientId: 'p4',
    date: '2026-01-22',
    type: 'imaging',
    title: 'CT ngực - Đánh giá sau hóa trị',
    summary: 'Khối u phổi giảm kích thước 40% so với trước. Không có di căn mới.',
    details: {
      findings: [
        'Khối u thùy trên phổi phải: 3.2cm (giảm từ 5.5cm)',
        'Không thấy hạch trung thất to',
        'Không có tràn dịch màng phổi',
        'Gan, lách, tụy không có tổn thương rõ',
        'Không thấy tổn thương di căn xương sườn',
      ],
      recommendations: [
        'Đáp ứng tốt với hóa trị liệu',
        'Tiếp tục chu kỳ điều trị theo kế hoạch',
        'Đánh giá lại sau 2 chu kỳ',
        'Theo dõi triệu chứng: ho máu, đau ngực, sụt cân',
      ],
      imageUrl: 'https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600',
    },
    uploadedBy: 'doctor',
  },
  {
    id: 'r7',
    patientId: 'p5',
    date: '2026-01-18',
    type: 'imaging',
    title: 'Điện tâm đồ (ECG)',
    summary: 'Nhịp xoang đều, có dấu hiệu thiếu máu cơ tim vùng trước.',
    details: {
      findings: [
        'Nhịp xoang, tần số 72 lần/phút',
        'Trục điện tim bình thường',
        'ST chênh xuống 1mm ở V2-V4',
        'Sóng T âm ở V3, V4',
        'Không có dấu hiệu nhồi máu cơ tim cấp',
      ],
      recommendations: [
        'Nghi ngờ thiếu máu cơ tim mạn tính',
        'Cần làm thêm test gắng sức hoặc CT mạch vành',
        'Tăng cường kiểm soát yếu tố nguy cơ: đái tháo đường, lipid máu',
        'Cân nhắc thêm thuốc chống đau thắt ngực',
      ],
      imageUrl: 'https://images.unsplash.com/photo-1628348068343-c6a848d2b6dd?w=600',
    },
    uploadedBy: 'doctor',
    alerts: ['Dấu hiệu thiếu máu cơ tim - cần đánh giá thêm'],
  },
];

// Mock alerts
export const mockAlerts: Alert[] = [
  {
    id: 'a1',
    patientId: 'p2',
    severity: 'critical',
    message: 'Bệnh nhân Trần Thị Bình - EF giảm xuống 42%, cần tái khám gấp',
    date: '2026-01-25',
    read: false,
  },
  {
    id: 'a2',
    patientId: 'p1',
    severity: 'warning',
    message: 'Nguyễn Văn An - HbA1c 7.8%, kiểm soát đường huyết chưa đạt mục tiêu',
    date: '2026-01-20',
    read: false,
  },
  {
    id: 'a3',
    patientId: 'p5',
    severity: 'warning',
    message: 'Hoàng Văn Em - ECG có dấu hiệu thiếu máu cơ tim, cần test gắng sức',
    date: '2026-01-18',
    read: true,
  },
];

// AI response templates
export const getAIResponse = (question: string, patientId: string): string => {
  const lowerQ = question.toLowerCase();
  const patient = mockPatients.find(p => p.id === patientId);
  const records = mockRecords.filter(r => r.patientId === patientId);
  const latestRecord = records[0];

  if (!patient || !latestRecord) return 'Xin lỗi, tôi không tìm thấy thông tin bệnh nhân này.';

  // Hypertension questions
  if (lowerQ.includes('cao huyết áp') || lowerQ.includes('huyết áp')) {
    if (patientId === 'p1') {
      return `**Tình trạng huyết áp hiện tại:**

Theo khám gần nhất (20/1/2026), bệnh nhân Nguyễn Văn An có huyết áp **160/95 mmHg**.

⚠️ **Đánh giá:** Huyết áp cao hơn mục tiêu (mục tiêu <140/90 mmHg cho bệnh nhân tăng huyết áp).

**Đã xử trí:**
- Tăng liều Amlodipine lên 10mg/ngày
- Đang dùng kết hợp với Losartan 50mg

**Khuyến nghị:**
- Theo dõi huyết áp tại nhà hàng ngày
- Hạn chế muối <5g/ngày
- Tái khám sau 4 tuần để đánh giá hiệu quả điều chỉnh thuốc

*Lưu ý: Đây là phân tích dựa trên dữ liệu hiện có, không thay thế quyết định lâm sàng của bác sĩ.*`;
    }
    return 'Bệnh nhân hiện có vấn đề về huyết áp. Vui lòng xem chi tiết trong hồ sơ bệnh án.';
  }

  // Diabetes questions
  if (lowerQ.includes('đường huyết') || lowerQ.includes('tiểu đường') || lowerQ.includes('hba1c')) {
    if (patientId === 'p1') {
      return `**Tình trạng đái tháo đường:**

**Xét nghiệm gần nhất (15/1/2026):**
- HbA1c: **7.8%** (mục tiêu <7%)
- Glucose lúc đói: **145 mg/dL** (mục tiêu 70-130 mg/dL)

⚠️ **Đánh giá:** Kiểm soát đường huyết chưa đạt mục tiêu.

**Thuốc hiện tại:**
- Metformin 850mg x 2 lần/ngày

**Khuyến nghị:**
- Cân nhắc tăng liều Metformin hoặc thêm thuốc thứ 2
- Chế độ ăn: hạn chế đường và tinh bột tinh luyện
- Tập thể dục đều đặn
- Theo dõi đường huyết tại nhà
- Xét nghiệm lại HbA1c sau 3 tháng

*HbA1c phản ánh mức đường huyết trung bình trong 3 tháng. Giá trị 7.8% cho thấy cần điều chỉnh điều trị.*`;
    }
    return 'Vui lòng xem kết quả xét nghiệm đường huyết trong hồ sơ bệnh nhân.';
  }

  // Imaging questions
  if (lowerQ.includes('x-ray') || lowerQ.includes('ct') || lowerQ.includes('chụp') || lowerQ.includes('hình ảnh')) {
    if (patientId === 'p4') {
      return `**Kết quả CT ngực (22/1/2026):**

✅ **Tin tốt:** Khối u phổi phải đáp ứng tốt với hóa trị

**Chi tiết:**
- Kích thước khối u: 3.2cm (giảm từ 5.5cm - giảm 40%)
- Không có tổn thương di căn mới
- Không tràn dịch màng phổi
- Các cơ quan khác không có bất thường

**Kế hoạch tiếp theo:**
- Tiếp tục chu kỳ hóa trị theo kế hoạch
- Đánh giá lại sau 2 chu kỳ
- Theo dõi triệu chứng: ho máu, khó thở, đau ngực, sụt cân

*Đây là dấu hiệu khả quan, cho thấy điều trị đang có hiệu quả.*`;
    }
    if (patientId === 'p2') {
      return `**Kết quả siêu âm tim (25/1/2026):**

⚠️ **Phát hiện quan trọng:**
- Phân suất tống máu (EF): **42%** (bình thường >55%)
- Chẩn đoán: **Suy tim có triệu chứng**

**Chi tiết:**
- Phì đại thất trái
- Hở van 2 lá nhẹ (độ 1/4)
- Tâm nhĩ trái tăng kích thước nhẹ

**Đã xử trí:**
- Bắt đầu thuốc điều trị suy tim
- Hạn chế muối <2g/ngày
- Hạn chế dịch

**Cần theo dõi sát - tái khám sau 1 tuần**

*EF <50% là dấu hiệu chức năng bơm máu của tim giảm, cần điều trị tích cực.*`;
    }
    return 'Vui lòng xem kết quả hình ảnh trong hồ sơ bệnh án.';
  }

  // ECG questions
  if (lowerQ.includes('ecg') || lowerQ.includes('điện tâm đồ') || lowerQ.includes('st')) {
    if (patientId === 'p5') {
      return `**Kết quả điện tâm đồ (18/1/2026):**

⚠️ **Phát hiện bất thường:**

**Các thay đổi ghi nhận:**
- Nhịp xoang đều, tần số 72 lần/phút
- **ST chênh xuống 1mm ở V2-V4**
- **Sóng T âm ở V3, V4**

**Ý nghĩa lâm sàng:**
Các thay đổi này gợi ý **thiếu máu cơ tim mạn tính** vùng trước (thành trước thất trái).

⚠️ Tuy nhiên, **không có dấu hiệu nhồi máu cơ tim cấp** (không có ST chênh lên).

**Khuyến nghị xử trí:**
1. Cần làm test gắng sức hoặc CT mạch vành để đánh giá mức độ hẹp động mạch
2. Kiểm soát chặt chẽ đường huyết và lipid máu
3. Cân nhắc thêm thuốc chống đau thắt ngực (nitrate, beta-blocker)
4. Theo dõi triệu chứng: đau ngực, khó thở khi gắng sức

*Không phải cấp cứu nhưng cần theo dõi và đánh giá thêm trong 1-2 tuần.*`;
    }
    return 'Vui lòng xem kết quả điện tâm đồ trong hồ sơ bệnh án.';
  }

  // Comparison questions
  if (lowerQ.includes('so với') || lowerQ.includes('trước') || lowerQ.includes('xấu hơn') || lowerQ.includes('tiến triển')) {
    return `**Đánh giá diễn tiến:**

Dựa trên dữ liệu hiện có, tôi thấy:

${patient.riskLevel === 'critical' ? '⚠️ **Tình trạng đang nặng và cần can thiệp tích cực**' : ''}
${patient.riskLevel === 'high' ? '⚠️ **Tình trạng cần theo dõi sát**' : ''}

**Các chỉ số quan trọng:**
${records.length > 1 ? `- Có ${records.length} bản ghi y tế gần đây\n- Đang trong quá trình theo dõi điều trị` : '- Mới có 1 lần khám gần đây'}

**Khuyến nghị:**
- Tiếp tục tuân thủ điều trị
- Tái khám đúng hẹn
- Báo ngay nếu có triệu chứng xấu đi

*Để so sánh chi tiết, vui lòng cung cấp thêm thông tin về thời điểm cụ thể cần so sánh.*`;
  }

  // Medication questions
  if (lowerQ.includes('thuốc') || lowerQ.includes('uống') || lowerQ.includes('medication')) {
    const meds = latestRecord.details.medications;
    if (meds && meds.length > 0) {
      return `**Đơn thuốc hiện tại:**

${meds.map(m => `**${m.name}**\n- Liều: ${m.dosage}\n- Cách dùng: ${m.frequency}`).join('\n\n')}

**Lưu ý:**
- Uống thuốc đúng giờ, đều đặn
- Không tự ý ngừng thuốc
- Báo ngay nếu có tác dụng phụ
- Mang theo danh sách thuốc khi đi khám

*Đây là đơn thuốc được kê gần nhất. Nếu có thắc mắc, vui lòng liên hệ bác sĩ.*`;
    }
  }

  // Default general response
  return `**Tổng quan bệnh nhân ${patient.name}:**

**Chẩn đoán:**
${latestRecord.details.diagnoses?.map(d => `- ${d}`).join('\n') || 'Xem trong hồ sơ bệnh án'}

**Tình trạng gần nhất:**
${latestRecord.summary}

**Mức độ nguy cơ:** ${patient.riskLevel === 'critical' ? '🔴 Nghiêm trọng' : patient.riskLevel === 'high' ? '🟠 Cao' : '🟡 Trung bình'}

**Tái khám:** ${patient.nextFollowUp}

Tôi có thể giúp bạn phân tích cụ thể hơn về:
- Huyết áp và kiểm soát tăng huyết áp
- Đường huyết và đái tháo đường
- Kết quả xét nghiệm, hình ảnh
- Thuốc đang sử dụng
- Kế hoạch theo dõi

Vui lòng hỏi cụ thể về vấn đề bạn quan tâm.

*Lưu ý: Đây là hệ thống hỗ trợ, không thay thế ý kiến của bác sĩ điều trị.*`;
};

// Patient-friendly AI responses
export const getPatientAIResponse = (question: string, patientId: string): string => {
  const lowerQ = question.toLowerCase();
  
  if (lowerQ.includes('cao huyết áp') || lowerQ.includes('huyết áp')) {
    return `**Tăng huyết áp là gì?**

Tăng huyết áp (cao huyết áp) là tình trạng áp lực máu lên thành mạch máu cao hơn bình thường.

**Chỉ số bình thường:**
- Huyết áp lý tưởng: <120/80 mmHg
- Huyết áp cao: ≥140/90 mmHg

**Tại sao cần quan tâm?**
Huyết áp cao kéo dài có thể làm tổn thương:
- ❤️ Tim (nhồi máu cơ tim, suy tim)
- 🧠 Não (đột quỵ)
- 👁️ Mắt (giảm thị lực)
- 🫁 Thận (suy thận)

**Cách kiểm soát:**
✅ Uống thuốc đều đặn theo đơn
✅ Ăn ít muối (<5g/ngày)
✅ Tập thể dục nhẹ thường xuyên
✅ Giảm căng thẳng
✅ Theo dõi huyết áp tại nhà

**Khi nào cần gặp bác sĩ gấp?**
🚨 Huyết áp >180/120
🚨 Đau đầu dữ dội, chóng mặt
🚨 Đau ngực, khó thở
🚨 Nhìn mờ đột ngột

*Hãy yên tâm - với điều trị đúng cách, huyết áp có thể kiểm soát tốt!*`;
  }

  if (lowerQ.includes('đường huyết') || lowerQ.includes('tiểu đường') || lowerQ.includes('hba1c')) {
    return `**Đái tháo đường là gì?**

Đái tháo đường là tình trạng đường huyết (glucose) trong máu cao hơn bình thường.

**Chỉ số bình thường:**
- Đường huyết lúc đói: 70-100 mg/dL
- HbA1c: <5.7%

**Chỉ số bệnh đái tháo đường:**
- Đường huyết lúc đói: ≥126 mg/dL
- HbA1c: ≥6.5%

**HbA1c là gì?**
Đây là xét nghiệm phản ánh mức đường huyết trung bình trong 3 tháng. Nó quan trọng hơn xét nghiệm đường huyết 1 lần.

**Tại sao cần kiểm soát?**
Đường huyết cao lâu ngày gây biến chứng:
- 👁️ Mù lòa
- 🫀 Bệnh tim mạch
- 🦵 Hoại tử chi
- 🫘 Suy thận

**Cách kiểm soát:**
✅ Uống thuốc đúng giờ
✅ Ăn ít đường, tinh bột trắng
✅ Tăng rau xanh, ngũ cốc nguyên hạt
✅ Tập thể dục 30 phút/ngày
✅ Theo dõi đường huyết tại nhà

**Triệu chứng cần gặp bác sĩ:**
🚨 Đường huyết >300 mg/dL
🚨 Khát nước nhiều, tiểu nhiều
🚨 Mệt mỏi, chóng mặt
🚨 Vết thương lâu lành

*Đái tháo đường có thể sống khỏe với điều trị đúng cách!*`;
  }

  if (lowerQ.includes('thuốc')) {
    return `**Hướng dẫn dùng thuốc:**

**Nguyên tắc quan trọng:**
✅ Uống đúng giờ, đều đặn
✅ Không tự ý bỏ liều
✅ Không tự ý ngừng thuốc
✅ Uống đủ nước

**Thuốc huyết áp:**
- Thường uống vào buổi sáng
- Có thể gây chóng mặn khi đứng dậy nhanh → đứng dậy từ từ

**Thuốc đái tháo đường:**
- Metformin: uống cùng hoặc sau bữa ăn (giảm khó tiêu)
- Nếu quên 1 liều: uống ngay khi nhớ ra, trừ khi gần giờ liều tiếp theo

**Tác dụng phụ cần báo bác sĩ:**
🚨 Chóng mặt nhiều
🚨 Buồn nôn kéo dài
🚨 Phát ban, ngứa
🚨 Ho khan (nếu dùng ACE-inhibitor)

**Mẹo nhớ uống thuốc:**
- Đặt chuông báo trên điện thoại
- Để thuốc ở nơi dễ thấy
- Uống cùng thói quen hàng ngày (vd: sau khi đánh răng)

*Thuốc là bạn đồng hành - hãy dùng đúng cách để bảo vệ sức khỏe!*`;
  }

  if (lowerQ.includes('ăn') || lowerQ.includes('chế độ') || lowerQ.includes('diet')) {
    return `**Chế độ ăn cho bệnh mạn tính:**

**Nguyên tắc chung:**
🥗 Nhiều rau xanh
🐟 Nhiều cá, ít thịt đỏ
🍚 Ít tinh bột trắng, nhiều ngũ cốc nguyên hạt
🧂 Ít muối, ít đường
💧 Uống đủ nước

**Thực phẩm nên ăn:**
✅ Rau xanh (nhiều loại)
✅ Cá hồi, cá thu
✅ Gạo lứt, yến mạch
✅ Đậu, các loại hạt
✅ Trái cây (vừa phải nếu có đái tháo đường)

**Thực phẩm nên hạn chế:**
❌ Muối, nước mắm, đồ muối
❌ Đường, nước ngọt, bánh kẹo
❌ Thịt mỡ, da gà, nội tạng
❌ Đồ chiên rán
❌ Fast food

**Lưu ý cho từng bệnh:**

**Cao huyết áp:**
- Muối <5g/ngày (1 thìa cà phê)
- Tăng thực phẩm giàu kali: chuối, khoai lang, rau xanh

**Đái tháo đường:**
- Ăn 3 bữa chính + 2-3 bữa phụ nhỏ
- Tránh ăn cơm trắng đơn thuần → kết hợp với rau
- Hạn chế trái cây ngọt (xoài, nhãn, vải)

**Mẹo:**
- Ăn chậm, nhai kỹ
- Ăn no 80% thôi
- Nấu ăn bằng hấp, luộc, nướng thay vì chiên

*Thay đổi từ từ, tạo thói quen lâu dài nhé!*`;
  }

  return `**Xin chào! Tôi có thể giúp bạn hiểu rõ hơn về:**

📊 **Bệnh của bạn**
- Tăng huyết áp là gì?
- Đái tháo đường là gì?
- Các chỉ số xét nghiệm nghĩa là gì?

💊 **Thuốc**
- Thuốc của bạn có tác dụng gì?
- Cách uống thuốc đúng cách
- Tác dụng phụ cần lưu ý

🍎 **Chế độ ăn uống**
- Nên ăn gì, tránh gì
- Cách nấu ăn tốt cho sức khỏe

⚠️ **Dấu hiệu cảnh báo**
- Khi nào cần gặp bác sĩ gấp
- Triệu chứng cần chú ý

**Hãy hỏi tôi bất cứ điều gì bạn thắc mắc!**

Ví dụ:
- "Cao huyết áp là gì?"
- "Thuốc Metformin có tác dụng gì?"
- "Tôi có thể ăn cơm không?"

*Lưu ý: Tôi chỉ cung cấp thông tin giáo dục, không thay thế lời khuyên của bác sĩ.*`;
};

export const getDiseaseInfo = (disease: DiseaseType) => {
  const info = {
    hypertension: {
      name: 'Tăng huyết áp',
      icon: '🫀',
      color: 'bg-red-100 text-red-800',
    },
    diabetes: {
      name: 'Đái tháo đường',
      icon: '🩸',
      color: 'bg-blue-100 text-blue-800',
    },
    cardiovascular: {
      name: 'Tim mạch',
      icon: '❤️',
      color: 'bg-purple-100 text-purple-800',
    },
    cancer: {
      name: 'Ung thư',
      icon: '🎗️',
      color: 'bg-pink-100 text-pink-800',
    },
    asthma: {
      name: 'Hen suyễn',
      icon: '🫁',
      color: 'bg-cyan-100 text-cyan-800',
    },
  };
  return info[disease];
};
