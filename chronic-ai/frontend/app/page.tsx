"use client";

import { useRouter } from "next/navigation";
import { Stethoscope, User } from "lucide-react";
import { useAuth } from "@/contexts";

export default function Home() {
  const router = useRouter();
  const { setRole } = useAuth();

  const selectRole = (role: "doctor" | "patient") => {
    // Keep auth context and persistence in sync before navigating.
    setRole(role);
    router.push("/dashboard");
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        backgroundImage:
          "linear-gradient(128.348deg, rgb(232, 244, 248) 3.4766%, rgb(171, 216, 255) 28.535%, rgb(224, 242, 254) 54.018%, rgb(232, 224, 254) 87.416%)",
      }}
    >
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-14 h-14 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[16px] flex items-center justify-center shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
              <Stethoscope className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-[#1e2939]">
              MediCare Pro
            </h1>
          </div>
          <p className="text-lg text-[#4a5565] max-w-2xl mx-auto">
            Hệ thống quản lý và chăm sóc bệnh nhân mạn tính từ xa
          </p>
          <p className="text-sm text-[#4a5565] mt-2">
            Remote Chronic Disease Management System
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <button
            onClick={() => selectRole("doctor")}
            className="group bg-[rgba(255,255,255,0.4)] rounded-[24px] shadow-[0px_8px_30px_0px_rgba(0,0,0,0.04)] hover:shadow-[0px_8px_30px_0px_rgba(0,0,0,0.08)] transition-all p-8 text-left border border-white"
          >
            <div className="w-16 h-16 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[16px] flex items-center justify-center mb-4 shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
              <Stethoscope className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-[#1e2939] mb-2">
              Bác sĩ
            </h2>
            <p className="text-[#4a5565] mb-4">
              Quản lý nhiều bệnh nhân, xem hồ sơ bệnh án, tải lên tài liệu y tế, trò chuyện với AI
            </p>
            <ul className="space-y-2 text-sm text-[#4a5565]">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Quản lý nhiều bệnh nhân
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Tải lên và phân tích tài liệu
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                AI hỗ trợ lâm sàng
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Cảnh báo và theo dõi
              </li>
            </ul>
            <div className="mt-6 text-[#4a9fd8] font-semibold group-hover:translate-x-1 transition-transform inline-block">
              Đăng nhập với vai trò Bác sĩ →
            </div>
          </button>

          <button
            onClick={() => selectRole("patient")}
            className="group bg-[rgba(255,255,255,0.4)] rounded-[24px] shadow-[0px_8px_30px_0px_rgba(0,0,0,0.04)] hover:shadow-[0px_8px_30px_0px_rgba(0,0,0,0.08)] transition-all p-8 text-left border border-white"
          >
            <div className="w-16 h-16 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[16px] flex items-center justify-center mb-4 shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
              <User className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-[#1e2939] mb-2">
              Bệnh nhân
            </h2>
            <p className="text-[#4a5565] mb-4">
              Xem hồ sơ sức khỏe cá nhân, hỏi AI về chẩn đoán và thuốc men, nhận nhắc nhở theo dõi
            </p>
            <ul className="space-y-2 text-sm text-[#4a5565]">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Xem hồ sơ bệnh án của bạn
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Hỏi AI về bệnh và thuốc
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Nhắc nhở theo dõi
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#4a9fd8] rounded-full"></span>
                Lịch hẹn và tư vấn
              </li>
            </ul>
            <div className="mt-6 text-[#4a9fd8] font-semibold group-hover:translate-x-1 transition-transform inline-block">
              Đăng nhập với vai trò Bệnh nhân →
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
