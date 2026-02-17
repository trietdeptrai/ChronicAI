"use client"

import { createContext, useContext, useState, type ReactNode } from "react"

export type DashboardLanguage = "vi" | "en"

interface DashboardLanguageContextType {
    language: DashboardLanguage
    setLanguage: (language: DashboardLanguage) => void
    toggleLanguage: () => void
}

const DASHBOARD_LANGUAGE_STORAGE_KEY = "dashboardLanguage"

const DashboardLanguageContext = createContext<DashboardLanguageContextType | null>(null)

function getInitialDashboardLanguage(): DashboardLanguage {
    if (typeof window === "undefined") return "vi"
    const stored = window.localStorage.getItem(DASHBOARD_LANGUAGE_STORAGE_KEY)
    return stored === "en" ? "en" : "vi"
}

export function DashboardLanguageProvider({ children }: { children: ReactNode }) {
    const [languageState, setLanguageState] = useState<DashboardLanguage>(() => getInitialDashboardLanguage())

    const setLanguage = (language: DashboardLanguage) => {
        setLanguageState(language)
        if (typeof window !== "undefined") {
            window.localStorage.setItem(DASHBOARD_LANGUAGE_STORAGE_KEY, language)
        }
    }

    const toggleLanguage = () => {
        setLanguage(languageState === "vi" ? "en" : "vi")
    }

    return (
        <DashboardLanguageContext.Provider value={{ language: languageState, setLanguage, toggleLanguage }}>
            {children}
        </DashboardLanguageContext.Provider>
    )
}

export function useDashboardLanguage() {
    const context = useContext(DashboardLanguageContext)
    if (!context) {
        throw new Error("useDashboardLanguage must be used within DashboardLanguageProvider")
    }
    return context
}
