import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../auth/SessionContext'

export default function AppHeader() {
  const { session, doLogout } = useSession()
  const navigate = useNavigate()

  async function handleLogout() {
    await doLogout()
    navigate(session?.role === 'admin' ? '/admin/login' : '/login', { replace: true })
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to={session?.role === 'admin' ? '/admin/settings' : '/app'} className="font-bold text-slate-900">
          AI 課業輔助系統
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {session?.role === 'student' && (
            <>
              <Link to="/app" className="text-slate-600 hover:text-slate-900">主系統</Link>
              <Link to="/history" className="text-slate-600 hover:text-slate-900">歷史紀錄</Link>
            </>
          )}
          {session?.role === 'admin' && (
            <Link to="/admin/settings" className="text-slate-600 hover:text-slate-900">系統設定</Link>
          )}
          {session && (
            <>
              <span className="text-slate-400">|</span>
              <span className="text-slate-500">
                {session.role === 'admin' ? 'Admin' : `學生 · ${session.display_name ?? ''}`}
              </span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-100"
              >
                登出
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
