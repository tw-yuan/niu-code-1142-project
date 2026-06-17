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
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { wsManager } from "../../lib/ws";
import { useAuthStore } from "../../store/auth";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const dashboardItem: NavItem = {
  to: "/dashboard",
  label: "儀表板",
  icon: BarChart3,
};
const documentsItem: NavItem = {
  to: "/documents",
  label: "文件",
  icon: FileText,
};
const chatItem: NavItem = {
  to: "/chat",
  label: "對話",
  icon: MessageSquareText,
};
const quizItem: NavItem = { to: "/quiz", label: "測驗", icon: Layers3 };
const flashcardsItem: NavItem = {
  to: "/flashcards",
  label: "閃卡",
  icon: BrainCircuit,
};
const notesItem: NavItem = { to: "/notes", label: "筆記", icon: NotebookPen };
const coursesItem: NavItem = { to: "/courses", label: "課程", icon: BookOpen };
const settingsItem: NavItem = {
  to: "/settings",
  label: "帳號設定",
  icon: Settings,
};
const adminItem: NavItem = { to: "/admin", label: "管理後台", icon: Shield };

function navSectionsForRole(role?: string): NavSection[] {
  const sections: NavSection[] = [
    {
      title: "學習區",
      items: [
        dashboardItem,
        documentsItem,
        chatItem,
        quizItem,
        flashcardsItem,
        notesItem,
      ],
    },
    { title: "課程區", items: [coursesItem] },
    { title: "帳號", items: [settingsItem] },
  ];
  if (role === "admin") {
    sections.splice(2, 0, { title: "管理區", items: [adminItem] });
  }
  return sections;
}

const mobilePrimaryItems = [
  dashboardItem,
  documentsItem,
  chatItem,
  coursesItem,
];

export function AppLayout() {
  const { user, logout, loadMe } = useAuthStore();
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const navSections = navSectionsForRole(user?.role);
  const mobileMoreSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !mobilePrimaryItems.some((primary) => primary.to === item.to),
      ),
    }))
    .filter((section) => section.items.length > 0);

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
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-zinc-200 bg-white md:flex">
        <div className="flex h-16 items-center border-b border-zinc-200 px-5">
          <div>
            <div className="text-lg font-semibold">LearnAI</div>
            <div className="text-xs text-zinc-500">學習輔助平台</div>
          </div>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto p-3">
          {navSections.map((section) => (
            <NavigationSection key={section.title} section={section} />
          ))}
        </nav>
        <div className="border-t border-zinc-200 p-4">
          <div className="mb-3 min-w-0">
            <div className="truncate text-sm font-medium">{user?.username}</div>
            <div className="truncate text-xs text-zinc-500">{user?.email}</div>
            <div className="mt-2 w-fit rounded-md bg-zinc-100 px-2 py-1 text-[11px] font-medium text-zinc-600">
              {roleLabel(user?.role)}
            </div>
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
        {mobilePrimaryItems.map((item) => (
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
          className="fixed inset-x-3 bottom-16 z-30 max-h-[70vh] overflow-y-auto rounded-lg border border-zinc-200 bg-white p-2 shadow-lg md:hidden"
        >
          {mobileMoreSections.map((section) => (
            <div key={section.title} className="py-1">
              <div className="px-3 py-2 text-xs font-semibold text-zinc-400">
                {section.title}
              </div>
              {section.items.map((item) => (
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
          ))}
        </div>
      )}
    </div>
  );
}

function NavigationSection({ section }: { section: NavSection }) {
  return (
    <div>
      <div className="mb-2 px-3 text-xs font-semibold text-zinc-400">
        {section.title}
      </div>
      <div className="space-y-1">
        {section.items.map((item) => (
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
      </div>
    </div>
  );
}

function roleLabel(role?: string) {
  if (role === "admin") return "管理員";
  if (role === "teacher") return "教師";
  return "學生";
}
