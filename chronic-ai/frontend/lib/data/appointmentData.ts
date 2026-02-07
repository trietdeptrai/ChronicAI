export interface Appointment {
  id: string;
  patientId: string | 'new'; // 'new' for new patients
  patientName: string;
  date: string;
  time: string;
  duration: number; // in minutes
  type: 'checkup' | 'followup' | 'emergency' | 'consultation';
  status: 'scheduled' | 'completed' | 'cancelled' | 'no-show';
  notes?: string;
  location?: string;
  isNewPatient?: boolean; // True if patient is new
  contactPhone?: string; // For new patients
  doctorName?: string; // Add this for compatibility
}

export const mockAppointments: Appointment[] = [
  // February 3, 2026
  {
    id: 'apt1',
    patientId: 'p1',
    patientName: 'Nguyễn Văn An',
    date: '2026-02-03',
    time: '09:00',
    duration: 30,
    type: 'followup',
    status: 'scheduled',
    notes: 'Kiểm tra huyết áp định kỳ',
    location: 'Phòng khám 1',
    isNewPatient: false,
    doctorName: 'BS. Nguyễn Thị B'
  },
  {
    id: 'apt2',
    patientId: 'new',
    patientName: 'Đỗ Văn Hải',
    date: '2026-02-03',
    time: '10:30',
    duration: 45,
    type: 'checkup',
    status: 'scheduled',
    notes: 'Bệnh nhân mới - Khám tổng quát',
    location: 'Phòng khám 1',
    isNewPatient: true,
    contactPhone: '0912345678',
    doctorName: 'BS. Trần Văn C'
  },
  {
    id: 'apt3',
    patientId: 'p2',
    patientName: 'Trần Thị Bình',
    date: '2026-02-03',
    time: '14:00',
    duration: 45,
    type: 'followup',
    status: 'scheduled',
    notes: 'Theo dõi điều trị tim mạch',
    location: 'Phòng khám 2',
    isNewPatient: false,
    doctorName: 'BS. Nguyễn Thị B'
  },
  // February 7, 2026 (Today)
  {
    id: 'apt7',
    patientId: 'p1',
    patientName: 'Nguyễn Văn An',
    date: '2026-02-07',
    time: '09:30',
    duration: 30,
    type: 'checkup',
    status: 'scheduled',
    notes: 'Xét nghiệm HbA1c định kỳ',
    location: 'Phòng khám 1',
    isNewPatient: false,
    doctorName: 'BS. Nguyễn Thị B'
  },
  {
    id: 'apt8',
    patientId: 'new',
    patientName: 'Ngô Minh Tuấn',
    date: '2026-02-07',
    time: '11:00',
    duration: 45,
    type: 'checkup',
    status: 'scheduled',
    notes: 'Bệnh nhân mới - Khám tim mạch',
    location: 'Phòng khám 2',
    isNewPatient: true,
    contactPhone: '0934567890',
    doctorName: 'BS. Trần Văn C'
  },
  // February 10, 2026
  {
    id: 'apt10',
    patientId: 'p2',
    patientName: 'Trần Thị Bình',
    date: '2026-02-10',
    time: '09:00',
    duration: 45,
    type: 'followup',
    status: 'scheduled',
    notes: 'Kiểm tra chỉ số tim mạch',
    location: 'Phòng khám 1',
    isNewPatient: false,
    doctorName: 'BS. Nguyễn Thị B'
  },
];

export const timeSlots = [
  '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
  '11:00', '11:30', '13:00', '13:30', '14:00', '14:30',
  '15:00', '15:30', '16:00', '16:30', '17:00'
];

export const appointmentTypes = [
  { value: 'checkup', label: 'Khám tổng quát', color: 'bg-blue-100 text-blue-700' },
  { value: 'followup', label: 'Tái khám', color: 'bg-green-100 text-green-700' },
  { value: 'emergency', label: 'Khẩn cấp', color: 'bg-red-100 text-red-700' },
  { value: 'consultation', label: 'Tư vấn', color: 'bg-purple-100 text-purple-700' },
];
