import { useEffect, useMemo, useState } from "react"
import { RefreshCw, Shield } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { apiFetch, CostStats } from "../lib/api"

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
  token_quota: number
  is_active: number
}

interface ReliabilityStats {
  fallback_count_7d: number
  by_reason: Record<string, number>
  daily_series: { date: string; count: number }[]
  events: Array<{ id: string; detail: Record<string, unknown>; created_at: string }>
}

export function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [cost, setCost] = useState<CostStats | null>(null)
  const [reliability, setReliability] = useState<ReliabilityStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [auditLogs, setAuditLogs] = useState<Array<Record<string, any>>>([])

  const featureRows = useMemo(
    () => Object.entries(cost?.this_month.by_feature ?? {}).map(([feature, total_usd]) => ({ feature, total_usd })),
    [cost],
  )

  async function load() {
    const [nextStats, nextUsers, nextCost, nextReliability, logs] = await Promise.all([
      apiFetch<AdminStats>("/admin/stats"),
      apiFetch<AdminUser[]>("/admin/users"),
      apiFetch<CostStats>("/admin/stats/cost"),
      apiFetch<ReliabilityStats>("/admin/stats/reliability"),
      apiFetch<Array<Record<string, any>>>("/admin/audit-logs?limit=20"),
    ])
    setStats(nextStats)
    setUsers(nextUsers)
    setCost(nextCost)
    setReliability(nextReliability)
    setAuditLogs(logs)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [])

  async function updateQuota(user: AdminUser, value: number) {
    await apiFetch(`/admin/users/${user.id}`, {
      method: "PUT",
      body: JSON.stringify({ token_quota: value }),
    })
    await load()
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">管理</h1>
          <p className="mt-1 text-sm text-zinc-500">成本、可靠性、使用者與 audit log</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm hover:bg-zinc-50" onClick={load}>
          <RefreshCw size={16} />
          重新整理
        </button>
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="使用者" value={stats?.users ?? 0} />
        <Stat label="文件" value={stats?.documents ?? 0} />
        <Stat label="Tokens" value={stats?.tokens_used ?? 0} />
        <Stat label="今日 USD" value={cost?.today.total_usd ?? 0} />
        <Stat label="本月 USD" value={cost?.this_month.total_usd ?? 0} />
      </div>
      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">Feature 成本</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="feature" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_usd" fill="#4f46e5" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">30 天成本</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cost?.daily_series ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="total_usd" stroke="#4f46e5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
            <Shield size={18} className="text-zinc-500" />
            <h2 className="font-semibold">使用者</h2>
          </div>
          <div className="divide-y divide-zinc-100">
            {users.map((user) => (
              <div key={user.id} className="grid gap-3 px-5 py-3 text-sm sm:grid-cols-[1fr_110px_160px] sm:items-center">
                <div>
                  <div className="font-medium">{user.username}</div>
                  <div className="text-xs text-zinc-500">{user.email}</div>
                </div>
                <div>{user.role} · {user.is_active ? "啟用" : "停用"}</div>
                <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" type="number" defaultValue={user.token_quota} onBlur={(event) => updateQuota(user, Number(event.target.value))} />
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold">可靠性</h2>
          <div className="mb-4 text-sm text-zinc-600">近 7 天 fallback：{reliability?.fallback_count_7d ?? 0}</div>
          <div className="space-y-2">
            {(reliability?.events ?? []).slice(0, 8).map((event) => (
              <div key={event.id} className="rounded-md bg-zinc-50 p-3 text-xs text-zinc-600">
                {event.created_at.slice(0, 19)} · {String(event.detail.reason ?? "unknown")} · {String(event.detail.model ?? "")}
              </div>
            ))}
          </div>
        </section>
      </div>
      <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-semibold">Audit logs</h2>
        </div>
        <div className="divide-y divide-zinc-100">
          {auditLogs.map((log) => (
            <div key={String(log.id)} className="grid gap-2 px-5 py-3 text-xs sm:grid-cols-[170px_180px_1fr]">
              <div className="text-zinc-500">{String(log.created_at).slice(0, 19)}</div>
              <div className="font-medium">{String(log.action)}</div>
              <div className="truncate text-zinc-500">{String(log.resource ?? "")}</div>
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
      <div className="mt-2 text-2xl font-semibold">{typeof value === "number" && value < 100 ? value.toFixed(4).replace(/\.?0+$/, "") : value.toLocaleString()}</div>
    </div>
  )
}
