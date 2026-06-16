import { useEffect } from "react"
import type { ReactNode } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { AppLayout } from "./components/app/AppLayout"
import { AdminPage } from "./pages/AdminPage"
import { ChatPage } from "./pages/ChatPage"
import { DashboardPage } from "./pages/DashboardPage"
import { DocumentsPage } from "./pages/DocumentsPage"
import { LoginPage } from "./pages/LoginPage"
import { PlaceholderPage } from "./pages/PlaceholderPage"
import { RegisterPage } from "./pages/RegisterPage"
import { useAuthStore } from "./store/auth"

export default function App() {
  const { loadMe } = useAuthStore()

  useEffect(() => {
    loadMe()
  }, [loadMe])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:sessionId" element={<ChatPage />} />
        <Route path="/quiz" element={<PlaceholderPage title="測驗" />} />
        <Route path="/quiz/generate" element={<PlaceholderPage title="測驗生成" />} />
        <Route path="/quiz/:id" element={<PlaceholderPage title="測驗作答" />} />
        <Route path="/quiz/wrongbook" element={<PlaceholderPage title="錯題本" />} />
        <Route path="/flashcards" element={<PlaceholderPage title="閃卡" />} />
        <Route path="/mindmap/:docId" element={<PlaceholderPage title="心智圖" />} />
        <Route path="/summary/:docId" element={<PlaceholderPage title="摘要" />} />
        <Route path="/settings" element={<PlaceholderPage title="設定" />} />
        <Route path="/admin" element={<AdminOnly><AdminPage /></AdminOnly>} />
      </Route>
    </Routes>
  )
}

function ProtectedLayout() {
  const { user, loading } = useAuthStore()
  const location = useLocation()
  if (loading) return <div className="min-h-screen bg-zinc-50" />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return <AppLayout />
}

function AdminOnly({ children }: { children: ReactNode }) {
  const user = useAuthStore((state) => state.user)
  if (user?.role !== "admin") return <Navigate to="/dashboard" replace />
  return children
}
