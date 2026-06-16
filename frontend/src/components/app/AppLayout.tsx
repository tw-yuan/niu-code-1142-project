import {
  BarChart3,
  BrainCircuit,
  BookOpen,
  Check,
  FileText,
  Layers3,
  LogOut,
  Menu,
  MessageSquareText,
  NotebookPen,
  Settings,
  Shield,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { wsManager } from "../../lib/ws";
import { useAuthStore } from "../../store/auth";

const navItems = [
  { to: "/dashboard", label: "儀表板", icon: BarChart3 },
  { to: "/documents", label: "文件", icon: FileText },
  { to: "/chat", label: "對話", icon: MessageSquareText },
  { to: "/quiz", label: "測驗", icon: Layers3 },
  { to: "/flashcards", label: "閃卡", icon: BrainCircuit },
  { to: "/notes", label: "筆記", icon: NotebookPen },
  { to: "/courses", label: "課程", icon: BookOpen },
  { to: "/settings", label: "設定", icon: Settings },
];

export function AppLayout() {
  const { user, logout, loadMe } = useAuthStore();
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) wsManager.connect(token);
    const off = wsManager.on("quota_warning", () =>
      loadMe().catch(() => undefined),
    );
    const offAnnouncement = wsManager.on("course_announcement", (message) => {
      setNotice(`新公告：${String(message.title ?? "")}`);
    });
    const offHelp = wsManager.on("course_help_request", (message) => {
      setNotice(`新求助：${String(message.title ?? "")}`);
    });
    const offHelpUpdate = wsManager.on("course_help_update", () => {
      setNotice("求助狀態已更新");
    });
    return () => {
      off();
      offAnnouncement();
      offHelp();
      offHelpUpdate();
    };
  }, [loadMe]);

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
              await logout();
              navigate("/login");
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
              本月 token 已使用 {user.quota_percent}%（
              {user.token_used_this_month.toLocaleString()} /{" "}
              {user.token_quota.toLocaleString()}）。
              {user.quota_status === "exceeded"
                ? "AI 功能已暫停，請聯絡管理員調整配額。"
                : "接近配額上限，請留意用量。"}
            </div>
          )}
          {notice && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-md border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
              <span>{notice}</span>
              <button
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-indigo-100"
                onClick={() => setNotice("")}
              >
                <Check size={14} />
                已讀
              </button>
            </div>
          )}
          <Outlet />
        </div>
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-zinc-200 bg-white md:hidden">
        {navItems.slice(0, 4).map((item) => (
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
        <button
          className={[
            "flex flex-col items-center gap-1 px-2 py-2 text-[11px]",
            moreOpen ? "text-indigo-700" : "text-zinc-500",
          ].join(" ")}
          onClick={() => setMoreOpen((value) => !value)}
          aria-expanded={moreOpen}
          aria-controls="mobile-more-menu"
        >
          <Menu size={18} />
          更多
        </button>
      </nav>
      {moreOpen && (
        <div
          id="mobile-more-menu"
          className="fixed inset-x-3 bottom-16 z-30 rounded-lg border border-zinc-200 bg-white p-2 shadow-lg md:hidden"
        >
          {[
            ...navItems.slice(4),
            ...(user?.role === "admin"
              ? [{ to: "/admin", label: "管理", icon: Shield }]
              : []),
          ].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-3 text-sm",
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-zinc-700 hover:bg-zinc-50",
                ].join(" ")
              }
              onClick={() => setMoreOpen(false)}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
