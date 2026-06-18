import {
  BarChart3,
  BrainCircuit,
  BookOpen,
  Check,
  ExternalLink,
  FileText,
  Layers3,
  LogOut,
  Menu,
  MessageSquareText,
  Network,
  NotebookPen,
  Settings,
  Shield,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { wsManager } from "../../lib/ws";
import { useAuthStore } from "../../store/auth";

type AppNotice = {
  message: string;
  to?: string;
};

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
const mindmapItem: NavItem = {
  to: "/mindmap",
  label: "心智圖",
  icon: Network,
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
        mindmapItem,
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
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const [notice, setNotice] = useState<AppNotice | null>(null);
  const wideWorkspace = location.pathname.startsWith("/mindmap");
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
      const courseId = stringValue(message.course_id);
      const announcementId = stringValue(message.announcement_id);
      setNotice({
        message: `新公告：${String(message.title ?? "")}`,
        to: courseInteractionPath(courseId, { announcement: announcementId }),
      });
    });
    const offHelp = wsManager.on("course_help_request", (message) => {
      const courseId = stringValue(message.course_id);
      const helpId = stringValue(message.help_request_id);
      setNotice({
        message: `新求助：${String(message.title ?? "")}`,
        to: courseInteractionPath(courseId, { help: helpId }),
      });
    });
    const offHelpUpdate = wsManager.on("course_help_update", (message) => {
      const courseId = stringValue(message.course_id);
      const helpId = stringValue(message.help_request_id);
      const title = stringValue(message.title);
      setNotice({
        message: helpUpdateNoticeText({
          title,
          eventType: stringValue(message.event_type),
          status: stringValue(message.status),
          message: stringValue(message.message),
        }),
        to: courseInteractionPath(courseId, { help: helpId }),
      });
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
          <div className="mb-3 flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">{user?.username}</div>
              <div className="truncate text-xs text-zinc-500">{user?.email}</div>
            </div>
            <div className="shrink-0 rounded-md bg-zinc-100 px-2 py-1 text-[11px] font-medium text-zinc-600">
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
        <div
          className={[
            "mx-auto min-h-screen px-4 pb-24 pt-5 sm:px-6 md:pb-5 lg:px-8",
            wideWorkspace ? "max-w-none" : "max-w-7xl",
          ].join(" ")}
        >
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
              {notice.to ? (
                <button
                  className="min-w-0 flex-1 truncate text-left font-medium hover:underline"
                  onClick={() => {
                    navigate(notice.to ?? "/courses");
                    setNotice(null);
                  }}
                >
                  {notice.message}
                </button>
              ) : (
                <span className="min-w-0 flex-1 truncate">{notice.message}</span>
              )}
              <div className="flex shrink-0 items-center gap-1">
                {notice.to && (
                  <button
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-indigo-100"
                    onClick={() => {
                      navigate(notice.to ?? "/courses");
                      setNotice(null);
                    }}
                  >
                    <ExternalLink size={14} />
                    查看
                  </button>
                )}
                <button
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-indigo-100"
                  onClick={() => setNotice(null)}
                >
                  <Check size={14} />
                  已讀
                </button>
              </div>
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

function stringValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function courseInteractionPath(
  courseId: string,
  target?: { help?: string; announcement?: string },
) {
  if (!courseId) return undefined;
  const params = new URLSearchParams({ course: courseId, tab: "interaction" });
  if (target?.help) params.set("help", target.help);
  if (target?.announcement) params.set("announcement", target.announcement);
  return `/courses?${params.toString()}`;
}

function helpStatusLabel(status: string) {
  if (status === "open") return "待處理";
  if (status === "in_progress") return "處理中";
  if (status === "resolved") return "已結案";
  return status || "已更新";
}

function helpUpdateNoticeText(input: {
  title: string;
  eventType: string;
  status: string;
  message: string;
}) {
  const suffix = input.title ? `：${input.title}` : "";
  if (input.eventType === "status_changed") {
    return `求助狀態改為${helpStatusLabel(input.status)}${suffix}`;
  }
  if (input.eventType === "assigned") return `求助已指派${suffix}`;
  if (input.eventType === "priority_changed") return `求助優先度已更新${suffix}`;
  if (input.eventType === "comment") return `求助有新留言${suffix}`;
  return `求助已更新${suffix}`;
}
