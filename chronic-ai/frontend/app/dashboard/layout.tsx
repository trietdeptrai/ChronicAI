"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/sidebar/sidebar"
import { DashboardLanguageProvider, useAuth, useDashboardLanguage } from "@/contexts"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const router = useRouter()
    const { role, isLoading } = useAuth()

    useEffect(() => {
        if (!isLoading && !role) {
            router.replace("/")
        }
    }, [isLoading, role, router])

    if (isLoading || !role) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <p className="text-sm text-gray-600">Loading dashboard...</p>
            </div>
        )
    }

    return (
        <DashboardLanguageProvider>
            <div
                className="min-h-screen flex"
                style={{
                    backgroundImage:
                        "linear-gradient(128.348deg, rgb(232, 244, 248) 3.4766%, rgb(171, 216, 255) 28.535%, rgb(224, 242, 254) 54.018%, rgb(232, 224, 254) 87.416%)",
                }}
            >
                <Sidebar />
                <main className="flex-1 overflow-y-auto p-6 md:p-8">
                    <div className="mb-4 flex justify-end">
                        <DashboardLanguageToggle />
                    </div>
                    {children}
                </main>
            </div>
        </DashboardLanguageProvider>
    )
}

function DashboardLanguageToggle() {
    const { language, setLanguage } = useDashboardLanguage()

    return (
        <div className="inline-flex items-center rounded-md border bg-background px-2 py-1 text-xs font-semibold shadow-sm">
            <button
                type="button"
                onClick={() => setLanguage("vi")}
                className={`rounded px-1.5 py-0.5 transition-colors ${
                    language === "vi"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                }`}
                aria-pressed={language === "vi"}
            >
                VN
            </button>
            <span className="px-1 text-muted-foreground">|</span>
            <button
                type="button"
                onClick={() => setLanguage("en")}
                className={`rounded px-1.5 py-0.5 transition-colors ${
                    language === "en"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                }`}
                aria-pressed={language === "en"}
            >
                EN
            </button>
        </div>
    )
}
