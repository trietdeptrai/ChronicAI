import { mockPatients, mockRecords, mockAlerts } from '@/lib/data/mockData';
import { mockAppointments } from '@/lib/data/appointmentData';
import { Users, Calendar, FileText, AlertCircle, TrendingUp, Activity, Heart, Pill, Stethoscope, Clock } from 'lucide-react';

export function DashboardHome() {
  const totalEHR = mockRecords.length;
  const totalAppointments = mockAppointments.filter(a => a.status === 'scheduled').length;
  const completedAppointments = mockAppointments.filter(a => a.status === 'completed').length;
  const criticalAlerts = mockAlerts.filter(a => a.severity === 'critical').length;
  const unreadAlerts = mockAlerts.filter(a => !a.read).length;
  const highRiskPatients = mockPatients.filter(p => p.riskLevel === 'critical' || p.riskLevel === 'high').length;

  // EHR breakdown by type
  const ehrByType = {
    diagnosis: mockRecords.filter(r => r.type === 'diagnosis').length,
    lab: mockRecords.filter(r => r.type === 'lab').length,
    imaging: mockRecords.filter(r => r.type === 'imaging').length,
    prescription: mockRecords.filter(r => r.type === 'prescription').length,
    visit: mockRecords.filter(r => r.type === 'visit').length,
    emergency: mockRecords.filter(r => r.type === 'emergency').length,
  };

  // Disease distribution
  const diseaseStats = {
    hypertension: mockPatients.filter(p => p.diseases.includes('hypertension')).length,
    diabetes: mockPatients.filter(p => p.diseases.includes('diabetes')).length,
    cardiovascular: mockPatients.filter(p => p.diseases.includes('cardiovascular')).length,
    cancer: mockPatients.filter(p => p.diseases.includes('cancer')).length,
    asthma: mockPatients.filter(p => p.diseases.includes('asthma')).length,
  };

  // Upcoming appointments in next 7 days
  const upcomingAppointments = mockAppointments.filter(a => {
    const appointmentDate = new Date(a.date);
    const today = new Date();
    const nextWeek = new Date();
    nextWeek.setDate(today.getDate() + 7);
    return a.status === 'scheduled' && appointmentDate >= today && appointmentDate <= nextWeek;
  }).length;

  return (
    <div className="space-y-6">
      {/* Top Stats Cards */}
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-[#4A9FD8]/20 to-[#2D88C4]/20 rounded-2xl flex items-center justify-center">
              <Users className="w-6 h-6 text-[#4A9FD8]" />
            </div>
            <h3 className="font-semibold text-[#4a5565]">Total Patients</h3>
          </div>
          <div className="text-4xl font-bold text-[#1e2939] mb-1">{mockPatients.length}</div>
          <div className="flex items-center gap-1 text-sm text-green-600">
            <TrendingUp className="w-4 h-4" />
            <span>12.8% from last month</span>
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-[#4A9FD8]/20 to-[#2D88C4]/20 rounded-2xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-[#4A9FD8]" />
            </div>
            <h3 className="font-semibold text-[#4a5565]">Total EHR</h3>
          </div>
          <div className="text-4xl font-bold text-[#1e2939] mb-1">{totalEHR}</div>
          <div className="flex items-center gap-1 text-sm text-[#4a5565]">
            <Activity className="w-4 h-4" />
            <span>Active records</span>
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-[#4A9FD8]/20 to-[#2D88C4]/20 rounded-2xl flex items-center justify-center">
              <Calendar className="w-6 h-6 text-[#4A9FD8]" />
            </div>
            <h3 className="font-semibold text-[#4a5565]">Appointments</h3>
          </div>
          <div className="text-4xl font-bold text-[#1e2939] mb-1">{totalAppointments}</div>
          <div className="flex items-center gap-1 text-sm text-[#4a5565]">
            <Clock className="w-4 h-4" />
            <span>{upcomingAppointments} this week</span>
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-red-100 to-red-50 rounded-2xl flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-500" />
            </div>
            <h3 className="font-semibold text-[#4a5565]">Critical Alerts</h3>
          </div>
          <div className="text-4xl font-bold text-[#1e2939] mb-1">{criticalAlerts}</div>
          <div className="flex items-center gap-1 text-sm text-red-600">
            <span>{unreadAlerts} unread</span>
          </div>
        </div>
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* EHR Breakdown */}
        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <h3 className="text-lg font-bold text-[#1e2939] mb-6">EHR by Type</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-[14px] flex items-center justify-center">
                  <Stethoscope className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Diagnosis</div>
                  <div className="text-xs text-[#4a5565]">Clinical assessments</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.diagnosis}</div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-[14px] flex items-center justify-center">
                  <Activity className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Lab Results</div>
                  <div className="text-xs text-[#4a5565]">Test reports</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.lab}</div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-[14px] flex items-center justify-center">
                  <FileText className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Imaging</div>
                  <div className="text-xs text-[#4a5565]">X-ray, CT, MRI</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.imaging}</div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-[14px] flex items-center justify-center">
                  <Pill className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Prescriptions</div>
                  <div className="text-xs text-[#4a5565]">Medication orders</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.prescription}</div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-teal-100 rounded-[14px] flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-teal-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Visits</div>
                  <div className="text-xs text-[#4a5565]">Patient visits</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.visit}</div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-red-100 rounded-[14px] flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <div className="font-semibold text-[#1e2939]">Emergency</div>
                  <div className="text-xs text-[#4a5565]">Urgent care</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-[#1e2939]">{ehrByType.emergency}</div>
            </div>
          </div>
        </div>

        {/* Disease Distribution & Risk Level */}
        <div className="space-y-6">
          {/* Disease Distribution */}
          <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
            <h3 className="text-lg font-bold text-[#1e2939] mb-6">Disease Distribution</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[rgba(74,159,216,0.1)] rounded-[16px] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Heart className="w-5 h-5 text-red-500" />
                  <span className="text-sm font-medium text-[#4a5565]">Hypertension</span>
                </div>
                <div className="text-3xl font-bold text-[#1e2939]">{diseaseStats.hypertension}</div>
              </div>

              <div className="bg-[rgba(74,159,216,0.1)] rounded-[16px] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-5 h-5 text-blue-500" />
                  <span className="text-sm font-medium text-[#4a5565]">Diabetes</span>
                </div>
                <div className="text-3xl font-bold text-[#1e2939]">{diseaseStats.diabetes}</div>
              </div>

              <div className="bg-[rgba(74,159,216,0.1)] rounded-[16px] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Heart className="w-5 h-5 text-pink-500" />
                  <span className="text-sm font-medium text-[#4a5565]">Cardiovascular</span>
                </div>
                <div className="text-3xl font-bold text-[#1e2939]">{diseaseStats.cardiovascular}</div>
              </div>

              <div className="bg-[rgba(74,159,216,0.1)] rounded-[16px] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-5 h-5 text-purple-500" />
                  <span className="text-sm font-medium text-[#4a5565]">Cancer</span>
                </div>
                <div className="text-3xl font-bold text-[#1e2939]">{diseaseStats.cancer}</div>
              </div>

              <div className="bg-[rgba(74,159,216,0.1)] rounded-[16px] p-4 col-span-2">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-5 h-5 text-teal-500" />
                  <span className="text-sm font-medium text-[#4a5565]">Asthma</span>
                </div>
                <div className="text-3xl font-bold text-[#1e2939]">{diseaseStats.asthma}</div>
              </div>
            </div>
          </div>

          {/* Risk Level Overview */}
          <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
            <h3 className="text-lg font-bold text-[#1e2939] mb-6">Patient Risk Levels</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-[14px]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="font-medium text-[#1e2939]">Critical</span>
                </div>
                <span className="text-xl font-bold text-red-600">
                  {mockPatients.filter(p => p.riskLevel === 'critical').length}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-orange-50 rounded-[14px]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                  <span className="font-medium text-[#1e2939]">High</span>
                </div>
                <span className="text-xl font-bold text-orange-600">
                  {mockPatients.filter(p => p.riskLevel === 'high').length}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-[14px]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <span className="font-medium text-[#1e2939]">Medium</span>
                </div>
                <span className="text-xl font-bold text-yellow-600">
                  {mockPatients.filter(p => p.riskLevel === 'medium').length}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-green-50 rounded-[14px]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="font-medium text-[#1e2939]">Low</span>
                </div>
                <span className="text-xl font-bold text-green-600">
                  {mockPatients.filter(p => p.riskLevel === 'low').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Stats */}
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#4a5565]">New Patients</h3>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <div className="text-3xl font-bold text-[#1e2939] mb-2">2</div>
          <div className="text-sm text-[#4a5565]">This month</div>
        </div>

        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#4a5565]">Completed</h3>
            <Calendar className="w-5 h-5 text-[#4A9FD8]" />
          </div>
          <div className="text-3xl font-bold text-[#1e2939] mb-2">{completedAppointments}</div>
          <div className="text-sm text-[#4a5565]">Appointments</div>
        </div>

        <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#4a5565]">High Risk</h3>
            <AlertCircle className="w-5 h-5 text-orange-500" />
          </div>
          <div className="text-3xl font-bold text-[#1e2939] mb-2">{highRiskPatients}</div>
          <div className="text-sm text-[#4a5565]">Patients need attention</div>
        </div>
      </div>
    </div>
  );
}
