import { mockPatients, mockRecords } from "@/lib/data/mockData";
import { PatientDetail } from "@/components/pages/PatientDetail";
import { AppointmentBooking } from "@/components/pages/AppointmentBooking";
import { User, LogOut, Calendar, FileText } from "lucide-react";
import { useState } from "react";

interface PatientDashboardProps {
  patientId: string;
  onLogout: () => void;
}

export function PatientDashboard({
  patientId,
  onLogout,
}: PatientDashboardProps) {
  const [activeView, setActiveView] = useState<
    "records" | "appointments"
  >("records");
  const patient = mockPatients.find((p) => p.id === patientId);
  const records = mockRecords.filter(
    (r) => r.patientId === patientId,
  );

  if (!patient) {
    return <div>Patient not found</div>;
  }

  return (
    <div
      className="min-h-screen"
      style={{
        backgroundImage:
          "linear-gradient(128.348deg, rgb(232, 244, 248) 3.4766%, rgb(171, 216, 255) 28.535%, rgb(224, 242, 254) 54.018%, rgb(232, 224, 254) 87.416%)",
      }}
    >
      {/* Header */}
      <header className="bg-[rgba(255,255,255,0.4)] border-b border-[rgba(255,255,255,0.3)] sticky top-0 z-30">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] rounded-xl flex items-center justify-center shadow-md">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">
                  ChronicAI
                </h1>
                <p className="text-sm text-gray-600">
                  Hồ sơ sức khỏe của bạn
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900">
                  {patient.name}
                </p>
                <p className="text-xs text-gray-500">
                  {patient.age} tuổi
                </p>
              </div>

              <button
                onClick={onLogout}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-white/40 rounded-xl transition-colors backdrop-blur-sm"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Đăng xuất</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Warning Banner */}
      <div className="bg-amber-50/60 backdrop-blur-sm border-b border-amber-200/40 px-6 py-3">
        <p className="text-sm text-amber-800 text-center">
          ⚠️ AI chỉ cung cấp thông tin tham khảo. Mọi quyết định
          điều trị cần tham khảo ý kiến bác sĩ.
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white/40 backdrop-blur-sm border-b border-white/30 px-6">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveView("records")}
            className={`px-6 py-3 font-medium transition-all relative ${
              activeView === "records"
                ? "text-[#4A9FD8]"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>Hồ sơ bệnh án</span>
            </div>
            {activeView === "records" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
            )}
          </button>

          <button
            onClick={() => setActiveView("appointments")}
            className={`px-6 py-3 font-medium transition-all relative ${
              activeView === "appointments"
                ? "text-[#4A9FD8]"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>Đặt lịch khám</span>
            </div>
            {activeView === "appointments" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
            )}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="h-[calc(100vh-177px)]">
        {activeView === "records" ? (
          <div className="overflow-y-auto h-full">
            <PatientDetail
              patientId={patientId}
              records={records}
              isDoctor={false}
            />
          </div>
        ) : (
          <div className="h-full p-6">
            <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] h-full">
              <AppointmentBooking
                patientId={patientId}
                patientName={patient.name}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
