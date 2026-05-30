import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useSession } from './SessionContext'

type Props = {
  children: ReactNode
  role?: 'student' | 'admin'
  redirectTo?: string
}

export default function RequireAuth({ children, role, redirectTo }: Props) {
  const { loading, session } = useSession()
  const location = useLocation()

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-slate-500">
        載入中…
      </main>
    )
  }

  if (!session) {
    const fallback = redirectTo ?? (role === 'admin' ? '/admin/login' : '/login')
    return <Navigate to={fallback} replace state={{ from: location.pathname }} />
  }

  if (role && session.role !== role) {
    const fallback = redirectTo ?? (role === 'admin' ? '/admin/login' : '/login')
    return <Navigate to={fallback} replace />
  }

  return <>{children}</>
}
