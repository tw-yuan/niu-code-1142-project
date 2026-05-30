import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminLogin } from '../api/auth'
import { ApiError } from '../api/client'
import { useSession } from '../auth/SessionContext'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const { setSession, session } = useSession()
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (session?.role === 'admin') {
    navigate('/admin/settings', { replace: true })
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!password) {
      setError('請輸入管理者密碼')
      return
    }
    setSubmitting(true)
    try {
      const info = await adminLogin(password)
      setSession(info)
      navigate('/admin/settings', { replace: true })
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail)
      } else {
        setError('登入失敗，請稍後再試')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="max-w-md w-full rounded-2xl border border-slate-200 bg-white shadow-sm p-8 space-y-5"
      >
        <div>
          <h1 className="text-2xl font-bold">管理者登入</h1>
          <p className="text-sm text-slate-500 mt-1">
            僅供系統管理者使用，學生請至 <a className="text-blue-600 hover:underline" href="/login">/login</a>。
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="admin-password" className="text-sm font-medium text-slate-700">
            管理者密碼
          </label>
          <input
            id="admin-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={submitting}
            required
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-slate-900 text-white py-2.5 font-medium hover:bg-slate-800 disabled:bg-slate-400 transition-colors"
        >
          {submitting ? '登入中…' : '進入後台'}
        </button>
      </form>
    </main>
  )
}
