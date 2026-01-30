export interface Appointment {
  id: string;
  patientId: string;
  patientName: string;
  date: string;
  time: string;
  duration: number; // in minutes
  type: 'checkup' | 'followup' | 'emergency' | 'consultation';
  status: 'scheduled' | 'completed' | 'cancelled' | 'no-show';
  notes?: string;
  location?: string;
}

export const mockAppointments: Appointment[] = [
  {
    id: 'apt1',
    patientId: 'p1',
    patientName: 'Nguyễn Văn An',
    date: '2026-01-28',
    time: '09:00',
    duration: 30,
    type: 'followup',
    status: 'scheduled',
    notes: 'Kiểm tra huyết áp định kỳ',
    location: 'Phòng khám 1'
  },
  {
    id: 'apt2',
    patientId: 'p2',
    patientName: 'Trần Thị Bình',
    date: '2026-01-28',
    time: '10:00',
    duration: 45,
    type: 'checkup',
    status: 'scheduled',
    notes: 'Xét nghiệm HbA1c',
    location: 'Phòng khám 1'
  },
  {
    id: 'apt3',
    patientId: 'p3',
    patientName: 'Lê Văn Cường',
    date: '2026-01-28',
    time: '14:00',
    duration: 30,
    type: 'followup',
    status: 'scheduled',
    notes: 'Theo dõi ECG',
    location: 'Phòng khám 2'
  },
  {
    id: 'apt4',
    patientId: 'p4',
    patientName: 'Phạm Thị Dung',
    date: '2026-01-29',
    time: '09:30',
    duration: 60,
    type: 'consultation',
    status: 'scheduled',
    notes: 'Tư vấn điều trị ung thư',
    location: 'Phòng khám 1'
  },
  {
    id: 'apt5',
    patientId: 'p5',
    patientName: 'Hoàng Văn Em',
    date: '2026-01-29',
    time: '11:00',
    duration: 30,
    type: 'followup',
    status: 'scheduled',
    notes: 'Kiểm tra chức năng hô hấp',
    location: 'Phòng khám 2'
  },
  {
    id: 'apt6',
    patientId: 'p1',
    patientName: 'Nguyễn Văn An',
    date: '2026-01-30',
    time: '10:00',
    duration: 30,
    type: 'checkup',
    status: 'scheduled',
    notes: 'Khám tổng quát',
    location: 'Phòng khám 1'
  },
  {
    id: 'apt7',
    patientId: 'p2',
    patientName: 'Trần Thị Bình',
    date: '2026-01-31',
    time: '09:00',
    duration: 45,
    type: 'followup',
    status: 'scheduled',
    notes: 'Kiểm tra đường huyết',
    location: 'Phòng khám 1'
  },
  {
    id: 'apt8',
    patientId: 'p3',
    patientName: 'Lê Văn Cường',
    date: '2026-02-03',
    time: '14:30',
    duration: 30,
    type: 'followup',
    status: 'scheduled',
    notes: 'Tái khám tim mạch',
    location: 'Phòng khám 2'
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
