import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { studentLogin } from '../api/auth'
import { ApiError } from '../api/client'
import { useSession } from '../auth/SessionContext'

export default function StudentLoginPage() {
  const navigate = useNavigate()
  const { setSession, session } = useSession()
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (session?.role === 'student') {
    navigate('/app', { replace: true })
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!nickname.trim()) {
      setError('請輸入暱稱')
      return
    }
    if (!password) {
      setError('請輸入密碼')
      return
    }
    setSubmitting(true)
    try {
      const info = await studentLogin(nickname.trim(), password)
      setSession(info)
      navigate('/app', { replace: true })
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
          <h1 className="text-2xl font-bold">學生登入</h1>
          <p className="text-sm text-slate-500 mt-1">
            輸入暱稱與共用密碼。同暱稱可看到先前的任務紀錄。
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="nickname" className="text-sm font-medium text-slate-700">
            暱稱
          </label>
          <input
            id="nickname"
            type="text"
            autoComplete="username"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={submitting}
            maxLength={40}
            required
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium text-slate-700">
            共用密碼
          </label>
          <input
            id="password"
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
          className="w-full rounded-lg bg-blue-600 text-white py-2.5 font-medium hover:bg-blue-700 disabled:bg-slate-400 transition-colors"
        >
          {submitting ? '登入中…' : '登入'}
        </button>

        <div className="text-xs text-slate-500 text-center">
          管理者請至 <a className="text-blue-600 hover:underline" href="/admin/login">/admin/login</a>
        </div>
      </form>
    </main>
  )
}
