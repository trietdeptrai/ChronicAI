/**
 * Dashboard home page with stats cards - matching reference design
 */
"use client"

import { useAuth } from "@/contexts"
import { useDashboardStats } from "@/lib/hooks"
import Link from "next/link"
import {
    Users,
    Calendar,
    Bell,
    TrendingUp,
    MessageSquare,
    FileText,
    ArrowRight,
    Heart,
    Activity,
} from "lucide-react"

const styles = {
    statsCard: {
        backgroundColor: "rgba(255, 255, 255, 0.6)",
        backdropFilter: "blur(12px)",
        borderRadius: "24px",
        padding: "24px",
        border: "1px solid rgba(255, 255, 255, 0.4)",
        boxShadow: "0 8px 30px rgba(0, 0, 0, 0.04)",
    },
    statsIconBlue: {
        width: "48px",
        height: "48px",
        borderRadius: "16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(to bottom right, rgba(74, 159, 216, 0.1), rgba(45, 136, 196, 0.1))",
    },
    statsIconRed: {
        width: "48px",
        height: "48px",
        borderRadius: "16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(to bottom right, #fef2f2, #fef2f2)",
    },
    statsIconGreen: {
        width: "48px",
        height: "48px",
        borderRadius: "16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(to bottom right, #f0fdf4, #f0fdf4)",
    },
    glassCard: {
        backgroundColor: "rgba(255, 255, 255, 0.6)",
        backdropFilter: "blur(12px)",
        borderRadius: "24px",
        padding: "24px",
        border: "1px solid rgba(255, 255, 255, 0.4)",
        boxShadow: "0 8px 30px rgba(0, 0, 0, 0.04)",
    },
    aiIcon: {
        width: "80px",
        height: "80px",
        background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
        borderRadius: "20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.1)",
    },
}

export default function DashboardPage() {
    const { role } = useAuth()
    const { data: stats, isLoading } = useDashboardStats()

    const isDoctor = role === "doctor"

    return (
        <div className="space-y-8">
            {/* Stats Cards - Doctor View */}
            {isDoctor && (
                <div className="grid grid-cols-3 gap-6">
                    {/* Total Patients */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconBlue}>
                                <Users className="w-6 h-6" style={{ color: "#4a9fd8" }} />
                            </div>
                            <h3 className="font-semibold text-gray-700">Tổng bệnh nhân</h3>
                        </div>
                        <div className="flex items-end justify-between">
                            <div>
                                <div className="text-4xl font-bold text-gray-800 mb-1">
                                    {isLoading ? "..." : (stats?.total_patients ?? 24)}
                                </div>
                                <div className="flex items-center gap-1 text-sm text-green-600">
                                    <TrendingUp className="w-4 h-4" />
                                    <span>12.8% tháng trước</span>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                            <span className="text-gray-600">Mới</span>
                            <span className="font-semibold text-gray-800">2</span>
                            <span className="text-gray-600">Cũ</span>
                            <span className="font-semibold text-gray-800">22</span>
                        </div>
                    </div>

                    {/* Appointments */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconBlue}>
                                <Calendar className="w-6 h-6" style={{ color: "#4a9fd8" }} />
                            </div>
                            <h3 className="font-semibold text-gray-700">Lịch hẹn</h3>
                        </div>
                        <div className="flex items-end justify-between">
                            <div>
                                <div className="text-4xl font-bold text-gray-800 mb-1">
                                    {isLoading ? "..." : (stats?.pending_consultations ?? 5)}
                                </div>
                                <div className="flex items-center gap-1 text-sm text-green-600">
                                    <TrendingUp className="w-4 h-4" />
                                    <span>1.9% tuần này</span>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                            <span className="text-gray-600">Tuần này</span>
                            <span className="font-semibold text-gray-800">3</span>
                            <span className="text-gray-600">Tuần sau</span>
                            <span className="font-semibold text-gray-800">2</span>
                        </div>
                    </div>

                    {/* Critical Alerts */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconRed}>
                                <Bell className="w-6 h-6 text-red-500" />
                            </div>
                            <h3 className="font-semibold text-gray-700">Cảnh báo</h3>
                        </div>
                        <div className="flex items-end justify-between">
                            <div>
                                <div className="text-4xl font-bold text-gray-800 mb-1">
                                    {isLoading ? "..." : (stats?.urgent_cases ?? 2)}
                                </div>
                                <div className="flex items-center gap-1 text-sm text-red-600">
                                    <span>Cần xử lý ngay</span>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-4 border-t border-gray-200/50 flex items-center justify-between text-sm">
                            <span className="text-gray-600">Chưa đọc</span>
                            <span className="font-semibold text-gray-800">{stats?.alerts ?? 3}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats Cards - Patient View */}
            {!isDoctor && (
                <div className="grid grid-cols-3 gap-6">
                    {/* Health Status */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconGreen}>
                                <Heart className="w-6 h-6 text-green-500" />
                            </div>
                            <h3 className="font-semibold text-gray-700">Sức khỏe hôm nay</h3>
                        </div>
                        <div className="text-4xl font-bold text-green-600 mb-1">Tốt</div>
                        <p className="text-sm text-gray-500">Dựa trên các chỉ số gần nhất</p>
                    </div>

                    {/* Last Checkup */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconBlue}>
                                <Activity className="w-6 h-6" style={{ color: "#4a9fd8" }} />
                            </div>
                            <h3 className="font-semibold text-gray-700">Lần khám gần nhất</h3>
                        </div>
                        <div className="text-4xl font-bold text-gray-800 mb-1">7 ngày</div>
                        <p className="text-sm text-gray-500">Trước đây</p>
                    </div>

                    {/* Medical Records */}
                    <div style={styles.statsCard}>
                        <div className="flex items-center gap-3 mb-4">
                            <div style={styles.statsIconBlue}>
                                <FileText className="w-6 h-6" style={{ color: "#4a9fd8" }} />
                            </div>
                            <h3 className="font-semibold text-gray-700">Hồ sơ bệnh án</h3>
                        </div>
                        <div className="text-4xl font-bold text-gray-800 mb-1">12</div>
                        <p className="text-sm text-gray-500">Tài liệu đã lưu</p>
                    </div>
                </div>
            )}

            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-6">
                {/* Main Content Area - Placeholder */}
                <div style={styles.glassCard}>
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">
                        {isDoctor ? "Danh sách bệnh nhân" : "Hồ sơ của tôi"}
                    </h3>
                    <div className="h-64 flex items-center justify-center text-gray-400">
                        <div className="text-center">
                            {isDoctor ? (
                                <>
                                    <Users className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p>Chọn &quot;Patients&quot; từ menu để xem danh sách</p>
                                </>
                            ) : (
                                <>
                                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                    <p>Chọn &quot;Records&quot; từ menu để xem hồ sơ</p>
                                </>
                            )}
                        </div>
                    </div>
                    <Link
                        href={isDoctor ? "/dashboard/patients" : "/dashboard/records"}
                        className="mt-4 inline-flex items-center font-semibold hover:underline"
                        style={{ color: "#4a9fd8" }}
                    >
                        Xem tất cả <ArrowRight className="ml-1 w-4 h-4" />
                    </Link>
                </div>

                {/* AI Chat Promotion */}
                <div style={styles.glassCard}>
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">
                        Trò chuyện với AI
                    </h3>
                    <div className="h-64 flex items-center justify-center">
                        <div className="text-center">
                            <div style={styles.aiIcon} className="mx-auto mb-4">
                                <MessageSquare className="w-10 h-10 text-white" />
                            </div>
                            <p className="text-gray-600 mb-2">
                                {isDoctor
                                    ? "Nhận hỗ trợ lâm sàng từ AI y tế"
                                    : "Hỏi đáp về sức khỏe bằng tiếng Việt"
                                }
                            </p>
                            <p className="text-sm text-gray-400">
                                Được hỗ trợ bởi MedGemma & Qwen 2.5
                            </p>
                        </div>
                    </div>
                    <Link
                        href="/dashboard/chat"
                        className="mt-4 inline-flex items-center font-semibold hover:underline"
                        style={{ color: "#4a9fd8" }}
                    >
                        Bắt đầu trò chuyện <ArrowRight className="ml-1 w-4 h-4" />
                    </Link>
                </div>
            </div>

            {/* Alert Banner for Doctors */}
            {isDoctor && stats && (stats.urgent_cases > 0 || stats.high_priority > 0) && (
                <div
                    className="p-4"
                    style={{
                        ...styles.glassCard,
                        borderLeft: "4px solid #ef4444",
                        backgroundColor: "rgba(254, 242, 242, 0.5)",
                    }}
                >
                    <div className="flex items-center gap-3">
                        <Bell className="w-5 h-5 text-red-500" />
                        <div className="flex-1">
                            <p className="font-semibold text-red-700">
                                Có {(stats.urgent_cases || 0) + (stats.high_priority || 0)} bệnh nhân cần chú ý
                            </p>
                            <p className="text-sm text-red-600">
                                {stats.urgent_cases || 0} khẩn cấp, {stats.high_priority || 0} ưu tiên cao
                            </p>
                        </div>
                        <Link
                            href="/dashboard/patients?priority=urgent,high"
                            className="px-4 py-2 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 transition-colors"
                        >
                            Xem ngay
                        </Link>
                    </div>
                </div>
            )}
        </div>
    )
}
