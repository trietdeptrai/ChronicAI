/**
 * Landing page with role selection
 * Vietnamese UI for doctors and patients - matching reference design
 */
"use client"

import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts"
import { Stethoscope, User } from "lucide-react"

// Style constants matching the reference design
const styles = {
  glassCard: {
    backgroundColor: "rgba(255, 255, 255, 0.4)",
    borderRadius: "24px",
    border: "1px solid white",
    boxShadow: "0 8px 30px rgba(0, 0, 0, 0.04)",
    transition: "all 0.3s ease",
  },
  glassCardHover: {
    boxShadow: "0 8px 30px rgba(0, 0, 0, 0.08)",
  },
  iconBox: {
    width: "64px",
    height: "64px",
    background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
    borderRadius: "16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.1)",
  },
  logoIconBox: {
    width: "56px",
    height: "56px",
    background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
    borderRadius: "16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.1)",
  },
  warningBox: {
    backgroundColor: "rgba(255, 255, 255, 0.4)",
    border: "1px solid white",
    borderRadius: "16px",
    boxShadow: "0 8px 30px rgba(0, 0, 0, 0.04)",
  },
}

export default function HomePage() {
  const router = useRouter()
  const { setRole } = useAuth()

  const handleRoleSelect = (role: "doctor" | "patient") => {
    setRole(role)
    router.push("/dashboard")
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div style={styles.logoIconBox}>
              <Stethoscope className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold" style={{ color: "#1e2939" }}>
              ChronicAI
            </h1>
          </div>
          <p className="text-lg max-w-2xl mx-auto" style={{ color: "#4a5565" }}>
            Hệ thống quản lý và chăm sóc bệnh nhân mạn tính từ xa
          </p>
          <p className="text-sm mt-2" style={{ color: "#4a5565" }}>
            Remote Chronic Disease Management System
          </p>
        </div>

        {/* Role Selection Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Doctor Card */}
          <button
            onClick={() => handleRoleSelect("doctor")}
            className="group p-8 text-left transition-all hover:-translate-y-1"
            style={styles.glassCard}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = styles.glassCardHover.boxShadow
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = styles.glassCard.boxShadow as string
            }}
          >
            <div style={styles.iconBox} className="mb-4">
              <Stethoscope className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: "#1e2939" }}>
              Bác sĩ
            </h2>
            <p className="mb-4" style={{ color: "#4a5565" }}>
              Quản lý nhiều bệnh nhân, xem hồ sơ bệnh án, tải lên tài liệu y tế, trò chuyện với AI
            </p>
            <ul className="space-y-2 text-sm" style={{ color: "#4a5565" }}>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Quản lý nhiều bệnh nhân
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Tải lên và phân tích tài liệu
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                AI hỗ trợ lâm sàng
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Cảnh báo và theo dõi
              </li>
            </ul>
            <div
              className="mt-6 font-semibold group-hover:translate-x-1 transition-transform inline-block"
              style={{ color: "#4a9fd8" }}
            >
              Đăng nhập với vai trò Bác sĩ →
            </div>
          </button>

          {/* Patient Card */}
          <button
            onClick={() => handleRoleSelect("patient")}
            className="group p-8 text-left transition-all hover:-translate-y-1"
            style={styles.glassCard}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = styles.glassCardHover.boxShadow
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = styles.glassCard.boxShadow as string
            }}
          >
            <div style={styles.iconBox} className="mb-4">
              <User className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: "#1e2939" }}>
              Bệnh nhân
            </h2>
            <p className="mb-4" style={{ color: "#4a5565" }}>
              Xem hồ sơ sức khỏe cá nhân, hỏi AI về chẩn đoán và thuốc men, nhận nhắc nhở theo dõi
            </p>
            <ul className="space-y-2 text-sm" style={{ color: "#4a5565" }}>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Xem hồ sơ bệnh án của bạn
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Hỏi AI về bệnh và thuốc
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Lời khuyên dễ hiểu
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#4a9fd8" }}></span>
                Nhắc nhở tái khám
              </li>
            </ul>
            <div
              className="mt-6 font-semibold group-hover:translate-x-1 transition-transform inline-block"
              style={{ color: "#4a9fd8" }}
            >
              Đăng nhập với vai trò Bệnh nhân →
            </div>
          </button>
        </div>

        {/* Warning Notice */}
        <div className="mt-8 p-4" style={styles.warningBox}>
          <p className="text-sm text-center" style={{ color: "#d97706" }}>
            ⚠️ <strong>Lưu ý quan trọng:</strong> Hệ thống AI chỉ mang tính hỗ trợ và giáo dục, không thay thế quyết định lâm sàng của bác sĩ.
            Đây là phiên bản demo với dữ liệu mẫu.
          </p>
        </div>
      </div>
    </main>
  )
}
