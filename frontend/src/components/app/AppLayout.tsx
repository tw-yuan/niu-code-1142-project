import {
  BarChart3,
  BrainCircuit,
  BookOpen,
  FileText,
  Layers3,
  LogOut,
  MessageSquareText,
  NotebookPen,
  Settings,
  Shield,
} from "lucide-react"
import { useEffect } from "react"
import { NavLink, Outlet, useNavigate } from "react-router-dom"
import { wsManager } from "../../lib/ws"
import { useAuthStore } from "../../store/auth"

const navItems = [
  { to: "/dashboard", label: "儀表板", icon: BarChart3 },
  { to: "/documents", label: "文件", icon: FileText },
  { to: "/chat", label: "對話", icon: MessageSquareText },
  { to: "/quiz", label: "測驗", icon: Layers3 },
  { to: "/flashcards", label: "閃卡", icon: BrainCircuit },
  { to: "/notes", label: "筆記", icon: NotebookPen },
  { to: "/courses", label: "課程", icon: BookOpen },
  { to: "/settings", label: "設定", icon: Settings },
]

export function AppLayout() {
  const { user, logout, loadMe } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (token) wsManager.connect(token)
    const off = wsManager.on("quota_warning", () => loadMe().catch(() => undefined))
    return () => {
      off()
    }
  }, [loadMe])

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-zinc-200 bg-white md:block">
        <div className="flex h-16 items-center border-b border-zinc-200 px-5">
          <div>
            <div className="text-lg font-semibold">LearnAI</div>
            <div className="text-xs text-zinc-500">學習輔助平台</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
                ].join(" ")
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
                ].join(" ")
              }
            >
              <Shield size={18} />
              管理
            </NavLink>
          )}
        </nav>
        <div className="absolute inset-x-0 bottom-0 border-t border-zinc-200 p-4">
          <div className="mb-3 min-w-0">
            <div className="truncate text-sm font-medium">{user?.username}</div>
            <div className="truncate text-xs text-zinc-500">{user?.email}</div>
          </div>
          <button
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
            onClick={async () => {
              await logout()
              navigate("/login")
            }}
          >
            <LogOut size={16} />
            登出
          </button>
        </div>
      </aside>
      <main className="md:pl-64">
        <div className="mx-auto min-h-screen max-w-7xl px-4 pb-24 pt-5 sm:px-6 md:pb-5 lg:px-8">
          {user && user.quota_status !== "ok" && (
            <div
              className={[
                "mb-4 rounded-md border px-4 py-3 text-sm",
                user.quota_status === "exceeded"
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-amber-200 bg-amber-50 text-amber-800",
              ].join(" ")}
            >
              本月 token 已使用 {user.quota_percent}%（{user.token_used_this_month.toLocaleString()} /{" "}
              {user.token_quota.toLocaleString()}）。{user.quota_status === "exceeded" ? "AI 功能已暫停，請聯絡管理員調整配額。" : "接近配額上限，請留意用量。"}
            </div>
          )}
          <Outlet />
        </div>
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-zinc-200 bg-white md:hidden">
        {navItems.slice(0, 5).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                "flex flex-col items-center gap-1 px-2 py-2 text-[11px]",
                isActive ? "text-indigo-700" : "text-zinc-500",
              ].join(" ")
            }
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
