import { useEffect } from "react"
import type { ReactNode } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { AppLayout } from "./components/app/AppLayout"
import { AdminPage } from "./pages/AdminPage"
import { ChatPage } from "./pages/ChatPage"
import { CoursesPage } from "./pages/CoursesPage"
import { DashboardPage } from "./pages/DashboardPage"
import { DocumentsPage } from "./pages/DocumentsPage"
import { FlashcardsPage } from "./pages/FlashcardsPage"
import { LoginPage } from "./pages/LoginPage"
import { MindmapPage } from "./pages/MindmapPage"
import { NotesPage } from "./pages/NotesPage"
import { QuizPage } from "./pages/QuizPage"
import { RegisterPage } from "./pages/RegisterPage"
import { SettingsPage } from "./pages/SettingsPage"
import { SummaryPage } from "./pages/SummaryPage"
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
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/quiz/generate" element={<QuizPage />} />
        <Route path="/quiz/:id" element={<QuizPage />} />
        <Route path="/quiz/wrongbook" element={<QuizPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/notes" element={<NotesPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/mindmap/:docId" element={<MindmapPage />} />
        <Route path="/summary/:docId" element={<SummaryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
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
