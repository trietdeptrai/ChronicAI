"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/sidebar/sidebar"
import { useAuth } from "@/contexts"

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
                <p className="text-sm text-gray-600">Đang tải dashboard...</p>
            </div>
        )
    }

    return (
        <div
            className="min-h-screen flex"
            style={{
                backgroundImage:
                    "linear-gradient(128.348deg, rgb(232, 244, 248) 3.4766%, rgb(171, 216, 255) 28.535%, rgb(224, 242, 254) 54.018%, rgb(232, 224, 254) 87.416%)",
            }}
        >
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-6 md:p-8">{children}</main>
        </div>
    )
}
