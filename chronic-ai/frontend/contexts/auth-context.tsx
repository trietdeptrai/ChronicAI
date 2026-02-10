/**
 * Auth Context - Placeholder for OTP authentication
 * TODO: Implement full Supabase Auth integration
 */
"use client"

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react"

export type UserRole = "patient" | "doctor" | null

interface User {
    id: string
    phone: string
    role: UserRole
    name?: string
}

interface AuthContextType {
    user: User | null
    role: UserRole
    isLoading: boolean
    isAuthenticated: boolean
    setRole: (role: UserRole) => void
    login: (phone: string, otp: string) => Promise<void>
    logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

function createDemoUser(role: Exclude<UserRole, null>): User {
    return {
        id: role === "doctor"
            ? "22222222-2222-4222-a222-222222222222"
            : "11111111-1111-4111-a111-111111111111",
        phone: "+84123456789",
        role,
        name: role === "doctor" ? "Bác sĩ Demo" : "Bệnh nhân Demo",
    }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [role, setRoleState] = useState<UserRole>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const storedRole = localStorage.getItem("userRole")
        if (storedRole === "doctor" || storedRole === "patient") {
            setRoleState(storedRole)
            setUser(createDemoUser(storedRole))
        }
        setIsLoading(false)
    }, [])

    const setRole = useCallback((newRole: UserRole) => {
        setRoleState(newRole)
        if (newRole) {
            localStorage.setItem("userRole", newRole)
            setUser(createDemoUser(newRole))
        } else {
            localStorage.removeItem("userRole")
            setUser(null)
        }
    }, [])

    const login = useCallback(async (phone: string, _otp: string) => {
        setIsLoading(true)
        // TODO: Implement actual Supabase OTP auth
        try {
            void _otp
            // Simulate login delay
            await new Promise(resolve => setTimeout(resolve, 1000))
            // For now, just set the user
            setUser({
                id: "auth-user",
                phone,
                role: role || "patient",
                name: "Người dùng",
            })
        } finally {
            setIsLoading(false)
        }
    }, [role])

    const logout = useCallback(() => {
        localStorage.removeItem("userRole")
        setUser(null)
        setRoleState(null)
    }, [])

    return (
        <AuthContext.Provider
            value={{
                user,
                role,
                isLoading,
                isAuthenticated: !!user,
                setRole,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error("useAuth must be used within AuthProvider")
    }
    return context
}
