import { Routes, Route, Navigate } from 'react-router-dom'
import StudentLoginPage from './pages/StudentLoginPage'
import AdminLoginPage from './pages/AdminLoginPage'
import MainAppPage from './pages/MainAppPage'
import TaskDetailPage from './pages/TaskDetailPage'
import HistoryPage from './pages/HistoryPage'
import AdminSettingsPage from './pages/AdminSettingsPage'
import NotFoundPage from './pages/NotFoundPage'
import { SessionProvider } from './auth/SessionContext'
import RequireAuth from './auth/RequireAuth'

export default function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<StudentLoginPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route
          path="/app"
          element={
            <RequireAuth role="student">
              <MainAppPage />
            </RequireAuth>
          }
        />
        <Route
          path="/tasks/:taskId"
          element={
            <RequireAuth role="student">
              <TaskDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/history"
          element={
            <RequireAuth>
              <HistoryPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <RequireAuth role="admin">
              <AdminSettingsPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </SessionProvider>
  )
}
