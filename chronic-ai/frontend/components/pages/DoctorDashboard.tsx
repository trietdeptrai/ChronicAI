import { useState } from 'react';
import { mockAlerts } from '@/lib/data/mockData';
import { AlertPanel } from '@/components/pages/AlertPanel';
import { Sidebar } from '@/components/pages/Sidebar';
import { CalendarView } from '@/components/pages/CalendarView';
import { ChatView } from '@/components/pages/ChatView';
import { PatientsPage } from '@/components/pages/PatientsPage';
import { DashboardHome } from '@/components/pages/DashboardHome';
import { SettingsPage } from '@/components/pages/SettingsPage';
import { Bell, Search } from 'lucide-react';

interface DoctorDashboardProps {
  onLogout: () => void;
}

export function DoctorDashboard({ onLogout }: DoctorDashboardProps) {
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [chatPatientContext, setChatPatientContext] = useState<string | null>(null);

  const unreadAlerts = mockAlerts.filter(a => !a.read).length;

  const handleOpenPatientEHR = (patientId: string) => {
    setSelectedPatientId(patientId);
    setActiveTab('patients');
  };

  const handleAskAIAboutPatient = (patientId: string) => {
    setChatPatientContext(patientId);
    setActiveTab('chat');
  };

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
              <AlertPanel 
                alerts={mockAlerts} 
                onClose={() => setShowAlerts(false)}
                onAlertClick={handleOpenPatientEHR}
              />
            </div>
          </div>
        )}

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {activeTab === 'calendar' ? (
            <CalendarView onOpenPatientEHR={handleOpenPatientEHR} />
          ) : activeTab === 'chat' ? (
            <ChatView onOpenPatientEHR={handleOpenPatientEHR} patientContext={chatPatientContext} />
          ) : activeTab === 'patients' ? (
            <PatientsPage 
              onOpenPatientEHR={handleOpenPatientEHR} 
              onAskAIAboutPatient={handleAskAIAboutPatient}
              preSelectedPatientId={selectedPatientId}
            />
          ) : activeTab === 'settings' ? (
            <SettingsPage />
          ) : (
            <DashboardHome />
          )}
        </div>
      </div>
    </div>
  );
}