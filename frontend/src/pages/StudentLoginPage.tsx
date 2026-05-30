import { useEffect, useState } from 'react'

export default function StudentLoginPage() {
  const [health, setHealth] = useState<string>('checking…')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((j) => setHealth(j.status ?? 'unknown'))
      .catch(() => setHealth('error'))
  }, [])

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-6">
      <div className="max-w-md w-full rounded-2xl border border-slate-200 bg-white shadow-sm p-8 space-y-4">
        <h1 className="text-xl font-bold">學生登入</h1>
        <p className="text-sm text-slate-600">
          M1 階段佔位頁 —— 後續 milestone 會接上實際登入表單。
        </p>
        <div className="text-xs text-slate-500">
          後端 /api/health：<span className="font-mono">{health}</span>
        </div>
        <div className="text-xs text-slate-500">
          管理者請至 <a className="text-blue-600 underline" href="/admin/login">/admin/login</a>
        </div>
      </div>
    </main>
  )
}
