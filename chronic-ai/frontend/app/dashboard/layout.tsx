/**
 * Dashboard layout with sidebar and header - matching reference design
 */
"use client"

import { Sidebar } from "@/components/sidebar"
import { useAuth } from "@/contexts"
import { Search, Bell } from "lucide-react"
import { useState } from "react"

const styles = {
    header: {
        backgroundColor: "rgba(255, 255, 255, 0.4)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.3)",
    },
    searchInput: {
        width: "320px",
        paddingLeft: "44px",
        paddingRight: "16px",
        paddingTop: "10px",
        paddingBottom: "10px",
        backgroundColor: "rgba(255, 255, 255, 0.6)",
        border: "1px solid rgba(255, 255, 255, 0.4)",
        borderRadius: "16px",
        fontSize: "14px",
        color: "#1e2939",
        outline: "none",
    },
    avatarIcon: {
        width: "36px",
        height: "36px",
        background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
        borderRadius: "14px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
    },
}

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const { user, role } = useAuth()
    const [showNotifications, setShowNotifications] = useState(false)

    // Mock unread notifications count
    const unreadCount = 3

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <header className="px-8 py-5" style={styles.header}>
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold mb-1" style={{ color: "#1e2939" }}>
                                Xin chào, {user?.name || "Người dùng"} 👋
                            </h1>
                            <p className="text-sm" style={{ color: "#4a5565" }}>
                                {role === "doctor"
                                    ? "Chúc bạn một ngày làm việc hiệu quả."
                                    : "Chúc bạn sức khỏe tốt hôm nay."
                                }
                            </p>
                        </div>

                        <div className="flex items-center gap-4">
                            {/* Search */}
                            <div className="relative">
                                <Search
                                    className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4"
                                    style={{ color: "#99a1af" }}
                                />
                                <input
                                    type="text"
                                    placeholder="Tìm kiếm..."
                                    style={styles.searchInput}
                                    className="placeholder:text-gray-400 focus:ring-2 focus:ring-blue-300/30"
                                />
                            </div>

                            {/* Notifications */}
                            <button
                                onClick={() => setShowNotifications(!showNotifications)}
                                className="relative p-2.5 hover:bg-white/60 rounded-[14px] transition-colors"
                            >
                                <Bell className="w-5 h-5" style={{ color: "#4a5565" }} />
                                {unreadCount > 0 && (
                                    <span
                                        className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
                                        style={{ backgroundColor: "#fb2c36" }}
                                    ></span>
                                )}
                            </button>

                            {/* Profile Avatar */}
                            <div style={styles.avatarIcon}>
                                <span className="text-white text-sm font-semibold">
                                    {user?.name?.charAt(0) || "U"}
                                </span>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-auto p-8">
                    {children}
                </main>
            </div>
        </div>
    )
}
