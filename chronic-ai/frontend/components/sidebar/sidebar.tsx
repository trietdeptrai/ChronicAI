/**
 * Sidebar navigation component - matching reference design
 */
"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { useAuth, useDashboardLanguage } from "@/contexts"
import {
    LayoutDashboard,
    Users,
    MessageSquare,
    Settings,
    LogOut,
    Calendar,
} from "lucide-react"

const styles = {
    sidebar: {
        width: "80px",
        backgroundColor: "rgba(255, 255, 255, 0.4)",
        borderRight: "1px solid rgba(255, 255, 255, 0.3)",
    },
    logoIcon: {
        width: "48px",
        height: "48px",
        background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
        borderRadius: "16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.1)",
    },
    activeNavItem: {
        background: "linear-gradient(to bottom, #4a9fd8, #2d88c4)",
        borderRadius: "14px",
        boxShadow: "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.1)",
    },
}

interface NavItem {
    id: string
    label: {
        vi: string
        en: string
    }
    href: string
    icon: React.ElementType
    doctorOnly?: boolean
    patientOnly?: boolean
}

const navItems: NavItem[] = [
    { id: "dashboard", label: { vi: "Bảng điều khiển", en: "Dashboard" }, href: "/dashboard", icon: LayoutDashboard },
    { id: "patients", label: { vi: "Bệnh nhân", en: "Patients" }, href: "/dashboard/patients", icon: Users, doctorOnly: true },
    { id: "calendar", label: { vi: "Lịch", en: "Calendar" }, href: "/dashboard/calendar", icon: Calendar },
    { id: "chat", label: { vi: "AI Chat", en: "AI Chat" }, href: "/dashboard/chat", icon: MessageSquare },
    { id: "settings", label: { vi: "Cài đặt", en: "Settings" }, href: "/dashboard/settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()
    const router = useRouter()
    const { role, logout } = useAuth()
    const { language } = useDashboardLanguage()

    const visibleItems = navItems.filter((item) => {
        if (item.doctorOnly && role !== "doctor") return false
        if (item.patientOnly && role !== "patient") return false
        return true
    })

    const handleLogout = () => {
        logout()
        router.push("/")
    }

    return (
        <aside
            className="flex flex-col items-center py-6 gap-4"
            style={styles.sidebar}
        >
            <div style={styles.logoIcon} className="mb-4">
                <LayoutDashboard className="w-6 h-6 text-white" />
            </div>

            <div className="flex flex-col gap-2 w-full px-3 flex-1">
                {visibleItems.map((item) => {
                    const Icon = item.icon
                    const isActive = pathname === item.href ||
                        (item.href !== "/dashboard" && pathname.startsWith(item.href))

                    return (
                        <Link
                            key={item.id}
                            href={item.href}
                            className={cn(
                                "w-full h-12 flex items-center justify-center transition-all",
                                !isActive && "hover:bg-white/60 rounded-[14px]"
                            )}
                            style={isActive ? styles.activeNavItem : undefined}
                            title={item.label[language]}
                        >
                            <Icon className={cn(
                                "w-5 h-5",
                                isActive ? "text-white" : "text-gray-600"
                            )} />
                        </Link>
                    )
                })}
            </div>

            <div className="px-3 w-full">
                <button
                    onClick={handleLogout}
                    className="w-full h-12 rounded-[14px] flex items-center justify-center transition-all hover:bg-red-100"
                    title={language === "vi" ? "Đăng xuất" : "Logout"}
                >
                    <LogOut className="w-5 h-5 text-red-500" />
                </button>
            </div>
        </aside>
    )
}
