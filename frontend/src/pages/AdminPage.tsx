import { useEffect, useState } from "react"
import { RefreshCw, Shield } from "lucide-react"
import { apiFetch } from "../lib/api"

interface AdminStats {
  users: number
  documents: number
  tokens_used: number
}

interface AdminUser {
  id: string
  username: string
  email: string
  role: string
  is_active: number
}

export function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])

  async function load() {
    const [nextStats, nextUsers] = await Promise.all([
      apiFetch<AdminStats>("/admin/stats"),
      apiFetch<AdminUser[]>("/admin/users"),
    ])
    setStats(nextStats)
    setUsers(nextUsers)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [])

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">管理</h1>
          <p className="mt-1 text-sm text-zinc-500">系統狀態</p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm hover:bg-zinc-50"
          onClick={load}
        >
          <RefreshCw size={16} />
          重新整理
        </button>
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Stat label="使用者" value={stats?.users ?? 0} />
        <Stat label="文件" value={stats?.documents ?? 0} />
        <Stat label="Tokens" value={stats?.tokens_used ?? 0} />
      </div>
      <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
          <Shield size={18} className="text-zinc-500" />
          <h2 className="font-semibold">使用者</h2>
        </div>
        <div className="divide-y divide-zinc-100">
          {users.map((user) => (
            <div key={user.id} className="grid grid-cols-[1fr_120px_100px] px-5 py-3 text-sm">
              <div>
                <div className="font-medium">{user.username}</div>
                <div className="text-xs text-zinc-500">{user.email}</div>
              </div>
              <div>{user.role}</div>
              <div>{user.is_active ? "啟用" : "停用"}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="text-sm text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  )
}

