import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { QueryProvider, AuthProvider } from "@/contexts"

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "vietnamese"],
})

export const metadata: Metadata = {
  title: "ChronicAI - Hệ thống Y tế Từ xa",
  description: "Ứng dụng telemedicine hỗ trợ quản lý bệnh mãn tính cho bệnh nhân và bác sĩ tuyến cơ sở tại Việt Nam",
  keywords: ["telemedicine", "chronic disease", "Vietnam", "healthcare", "AI"],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <QueryProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
