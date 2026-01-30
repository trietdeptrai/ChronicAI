import { useState } from 'react';
import { mockPatients, mockRecords, mockAlerts } from '@/data/mockData';
import { PatientList } from '@/app/components/PatientList';
import { PatientDetail } from '@/app/components/PatientDetail';
import { AlertPanel } from '@/app/components/AlertPanel';
import { Sidebar } from '@/app/components/Sidebar';
import { CalendarView } from '@/app/components/CalendarView';
import { Stethoscope, Bell, LogOut, Search, TrendingUp, Users, Calendar as CalendarIcon } from 'lucide-react';

interface DoctorDashboardProps {
  onLogout: () => void;
}

export function DoctorDashboard({ onLogout }: DoctorDashboardProps) {
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [activeTab, setActiveTab] = useState('patients');

  const unreadAlerts = mockAlerts.filter(a => !a.read).length;

  return (
    <div className="min-h-screen flex" style={{ backgroundImage: "linear-gradient(128.348deg, rgb(232, 244, 248) 3.4766%, rgb(171, 216, 255) 28.535%, rgb(224, 242, 254) 54.018%, rgb(232, 224, 254) 87.416%)" }}>
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-[rgba(255,255,255,0.4)] border-b border-[rgba(255,255,255,0.3)] px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#1e2939] mb-1">Good Morning, Dr. Ashlynn 👋</h1>
              <p className="text-sm text-[#4a5565]">Your progress this week is Awesome.</p>
            </div>

            <div className="flex items-center gap-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#99a1af]" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="w-80 pl-11 pr-4 py-2.5 bg-[rgba(255,255,255,0.6)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-sm text-[rgba(10,10,10,0.5)] placeholder:text-[rgba(10,10,10,0.5)]"
                />
              </div>

              {/* Alerts */}
              <button
                onClick={() => setShowAlerts(!showAlerts)}
                className="relative p-2.5 hover:bg-[rgba(255,255,255,0.6)] rounded-[14px] transition-colors"
              >
                <Bell className="w-5 h-5 text-[#4a5565]" />
                {unreadAlerts > 0 && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#fb2c36] rounded-full"></span>
                )}
              </button>

              {/* Profile */}
              <button onClick={onLogout} className="flex items-center gap-3 hover:bg-[rgba(255,255,255,0.6)] rounded-[14px] px-3 py-2 transition-colors">
                <div className="w-9 h-9 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[14px] flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">DA</span>
                </div>
              </button>
            </div>
          </div>
        </header>

        {/* Alert Panel */}
        {showAlerts && (
          <div className="fixed inset-0 bg-black/5 z-40" onClick={() => setShowAlerts(false)}>
            <div className="absolute right-4 top-20 w-96" onClick={(e) => e.stopPropagation()}>
              <AlertPanel alerts={mockAlerts} onClose={() => setShowAlerts(false)} />
            </div>
          </div>
        )}

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {activeTab === 'calendar' ? (
            <CalendarView />
          ) : (
            <>
              {/* Stats Cards */}
              <div className="grid grid-cols-3 gap-6 mb-8">
                <div className="bg-white/60 backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-[#4A9FD8]/10 to-[#2D88C4]/10 rounded-2xl flex items-center justify-center">
                      <Users className="w-6 h-6 text-[#4A9FD8]" />
                    </div>
                    <h3 className="font-semibold text-gray-700">Total Patient</h3>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-4xl font-bold text-gray-800 mb-1">{mockPatients.length}</div>
                      <div className="flex items-center gap-1 text-sm text-green-600">
                        <TrendingUp className="w-4 h-4" />
                        <span>12.8% the last month</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                    <span className="text-gray-600">New patient</span>
                    <span className="font-semibold text-gray-800">2</span>
                    <span className="text-gray-600">Old patient</span>
                    <span className="font-semibold text-gray-800">{mockPatients.length - 2}</span>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-[#4A9FD8]/10 to-[#2D88C4]/10 rounded-2xl flex items-center justify-center">
                      <CalendarIcon className="w-6 h-6 text-[#4A9FD8]" />
                    </div>
                    <h3 className="font-semibold text-gray-700">Appointments</h3>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-4xl font-bold text-gray-800 mb-1">
                        {mockPatients.filter(p => new Date(p.nextFollowUp) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)).length}
                      </div>
                      <div className="flex items-center gap-1 text-sm text-green-600">
                        <TrendingUp className="w-4 h-4" />
                        <span>1.9% this week</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                    <span className="text-gray-600">This week</span>
                    <span className="font-semibold text-gray-800">3</span>
                    <span className="text-gray-600">Next week</span>
                    <span className="font-semibold text-gray-800">2</span>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-md rounded-3xl p-6 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-red-100 to-red-50 rounded-2xl flex items-center justify-center">
                      <Bell className="w-6 h-6 text-red-500" />
                    </div>
                    <h3 className="font-semibold text-gray-700">Critical Alerts</h3>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-4xl font-bold text-gray-800 mb-1">
                        {mockAlerts.filter(a => a.severity === 'critical').length}
                      </div>
                      <div className="flex items-center gap-1 text-sm text-red-600">
                        <span>Requires immediate attention</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                    <span className="text-gray-600">Unread</span>
                    <span className="font-semibold text-gray-800">{unreadAlerts}</span>
                  </div>
                </div>
              </div>

              {/* Main Content Area */}
              <div className="grid grid-cols-[400px_1fr] gap-6">
                {/* Patient List */}
                <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
                  <PatientList
                    patients={mockPatients}
                    selectedPatientId={selectedPatientId}
                    onSelectPatient={setSelectedPatientId}
                  />
                </div>

                {/* Patient Detail */}
                <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
                  {selectedPatientId ? (
                    <PatientDetail
                      patientId={selectedPatientId}
                      records={mockRecords.filter(r => r.patientId === selectedPatientId)}
                      isDoctor={true}
                    />
                  ) : (
                    <div className="h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Stethoscope className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p className="text-lg">Select a patient to view details</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}