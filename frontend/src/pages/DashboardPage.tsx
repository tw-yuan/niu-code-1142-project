import {
  BookOpen,
  BrainCircuit,
  FileText,
  Layers3,
  ListTodo,
  Megaphone,
  MessageCircleQuestion,
  MessageSquareText,
  Settings,
  Shield,
  TrendingUp,
  Users,
  Clock3,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GenerationTaskList } from "../components/app/GenerationTaskPanel";
import {
  apiFetch,
  CourseDashboard,
  DocumentItem,
  FlashcardItem,
  GenerationTask,
} from "../lib/api";
import { useAuthStore } from "../store/auth";

interface QuickAction {
  title: string;
  description: string;
  to: string;
  icon: LucideIcon;
  badge?: string;
  primary?: boolean;
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [tasks, setTasks] = useState<Array<Record<string, any>>>([]);
  const [generationTasks, setGenerationTasks] = useState<GenerationTask[]>([]);
  const [flashcards, setFlashcards] = useState<FlashcardItem[]>([]);
  const [courseDashboard, setCourseDashboard] = useState<CourseDashboard>({
    announcements: [],
    help_requests: [],
    managed_help_count: 0,
  });

  async function loadGenerationTasks() {
    const data = await apiFetch<GenerationTask[]>(
      "/generation/tasks?active_only=true&limit=20",
    ).catch(() => []);
    setGenerationTasks(data);
  }

  useEffect(() => {
    apiFetch<DocumentItem[]>("/documents")
      .then(setDocuments)
      .catch(() => setDocuments([]));
    apiFetch<{ tasks: Array<Record<string, any>> }>("/goals/today")
      .then((data) => setTasks(data.tasks))
      .catch(() => setTasks([]));
    apiFetch<FlashcardItem[]>("/flashcards")
      .then(setFlashcards)
      .catch(() => setFlashcards([]));
    apiFetch<CourseDashboard>("/courses/dashboard")
      .then(setCourseDashboard)
      .catch(() =>
        setCourseDashboard({
          announcements: [],
          help_requests: [],
          managed_help_count: 0,
        }),
      );
    loadGenerationTasks();
  }, []);

  useEffect(() => {
    if (
      !generationTasks.some((task) =>
        ["queued", "running"].includes(task.status),
      )
    ) {
      return;
    }
    const timer = window.setInterval(() => {
      loadGenerationTasks();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [generationTasks]);

  const ready = documents.filter((doc) => doc.status === "ready").length;
  const processing = documents.filter(
    (doc) => doc.status !== "ready" && doc.status !== "error",
  ).length;
  const due = flashcards.filter(
    (card) => card.next_review <= new Date().toISOString(),
  ).length;
  const quickActions = getQuickActions(
    user?.role,
    due,
    courseDashboard.managed_help_count,
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">儀表板</h1>
        <p className="mt-1 text-sm text-zinc-500">本週學習狀態</p>
      </div>
      <section className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {quickActions.map((action) => (
          <QuickActionCard key={action.to + action.title} action={action} />
        ))}
      </section>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric title="文件總數" value={documents.length} icon={FileText} />
        <Metric title="可用文件" value={ready} icon={TrendingUp} />
        <Metric title="處理中" value={processing} icon={MessageSquareText} />
        <Metric title="待複習" value={due} icon={BrainCircuit} />
      </div>
      {generationTasks.length > 0 && (
        <section className="mt-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
            <Clock3 size={18} className="text-zinc-500" />
            <h2 className="font-semibold">生成任務狀態</h2>
          </div>
          <GenerationTaskList
            tasks={generationTasks}
            emptyText="目前沒有生成任務"
          />
        </section>
      )}
      <section className="mt-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
          <ListTodo size={18} className="text-zinc-500" />
          <h2 className="font-semibold">今日任務</h2>
        </div>
        <div className="divide-y divide-zinc-100">
          {tasks.map((task, index) => (
            <Link
              key={index}
              className="block px-5 py-3 text-sm hover:bg-zinc-50"
              to={taskHref(task)}
            >
              <div className="font-medium">{taskLabel(task)}</div>
              <div className="text-xs text-zinc-500">
                {String(task.doc_title ?? task.type)}
              </div>
            </Link>
          ))}
          {tasks.length === 0 && (
            <div className="px-5 py-8 text-sm text-zinc-500">
              尚無任務。可先從 ready 文件開始對話、生成測驗或建立閃卡。
            </div>
          )}
        </div>
      </section>
      {(courseDashboard.announcements.length > 0 ||
        courseDashboard.help_requests.length > 0) && (
        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-zinc-200 bg-white shadow-sm">
            <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
              <Megaphone size={18} className="text-zinc-500" />
              <h2 className="font-semibold">未讀公告</h2>
            </div>
            <div className="divide-y divide-zinc-100">
              {courseDashboard.announcements.map((item) => (
                <Link
                  key={item.id}
                  className="block px-5 py-3 text-sm hover:bg-zinc-50"
                  to={`/courses?course=${item.course_id}&tab=interaction`}
                >
                  <div className="font-medium">{item.title}</div>
                  <div className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-500">
                    {item.course_title} · {item.content}
                  </div>
                </Link>
              ))}
              {courseDashboard.announcements.length === 0 && (
                <div className="px-5 py-8 text-sm text-zinc-500">
                  沒有未讀公告
                </div>
              )}
            </div>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white shadow-sm">
            <div className="flex items-center gap-2 border-b border-zinc-200 px-5 py-4">
              <MessageCircleQuestion size={18} className="text-zinc-500" />
              <h2 className="font-semibold">待處理求助</h2>
            </div>
            <div className="divide-y divide-zinc-100">
              {courseDashboard.help_requests.map((item) => (
                <Link
                  key={item.id}
                  className="block px-5 py-3 text-sm hover:bg-zinc-50"
                  to={`/courses?course=${item.course_id}&tab=interaction`}
                >
                  <div className="font-medium">{item.title}</div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {item.course_title} · {item.username ?? item.user_id} ·{" "}
                    {helpStatusLabel(item.status)}
                  </div>
                </Link>
              ))}
              {courseDashboard.help_requests.length === 0 && (
                <div className="px-5 py-8 text-sm text-zinc-500">
                  沒有待處理求助
                </div>
              )}
            </div>
          </div>
        </section>
      )}
      <section className="mt-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-semibold">最近文件</h2>
        </div>
        <div className="divide-y divide-zinc-100">
          {documents.slice(0, 6).map((doc) => (
            <div
              key={doc.id}
              className="flex flex-col gap-3 px-5 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="text-sm font-medium">{doc.filename}</div>
                <div className="text-xs text-zinc-500">{doc.file_type}</div>
              </div>
              {doc.status === "ready" ? (
                <div className="flex flex-wrap gap-2">
                  <Link
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                    to={`/chat?doc=${doc.id}`}
                  >
                    對話
                  </Link>
                  <Link
                    className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-700 hover:bg-zinc-50"
                    to={`/quiz/generate?doc=${doc.id}`}
                  >
                    測驗
                  </Link>
                  <Link
                    className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-700 hover:bg-zinc-50"
                    to={`/documents/${doc.id}`}
                  >
                    查看
                  </Link>
                </div>
              ) : (
                <span className="w-fit rounded-lg bg-zinc-100 px-2 py-1 text-xs text-zinc-600">
                  {doc.status}
                </span>
              )}
            </div>
          ))}
          {documents.length === 0 && (
            <div className="px-5 py-8 text-sm text-zinc-500">尚無文件</div>
          )}
        </div>
      </section>
    </div>
  );
}

function getQuickActions(
  role: string | undefined,
  due: number,
  managedHelpCount: number,
): QuickAction[] {
  if (role === "admin") {
    return [
      {
        title: "管理後台",
        description: "查看成本、可靠性與系統狀態",
        to: "/admin",
        icon: Shield,
        primary: true,
      },
      {
        title: "使用者管理",
        description: "調整角色、狀態與配額",
        to: "/admin?tab=users",
        icon: Users,
      },
      {
        title: "資源稽核",
        description: "檢查文件、對話與課程資料",
        to: "/admin?tab=resources",
        icon: FileText,
      },
      {
        title: "系統設定",
        description: "管理 LLM provider 與模型設定",
        to: "/admin?tab=settings",
        icon: Settings,
      },
    ];
  }

  if (role === "teacher") {
    return [
      {
        title: "課程管理",
        description: "管理教材、成員、公告與進度",
        to: "/courses",
        icon: BookOpen,
        primary: true,
      },
      {
        title: "共享教材",
        description: "上傳教材並加入課程範圍",
        to: "/documents",
        icon: FileText,
      },
      {
        title: "建立課程測驗",
        description: "從教材產生題目並發布",
        to: "/quiz/generate",
        icon: Layers3,
      },
      {
        title: "待處理求助",
        description: "回覆學生在課程中的問題",
        to: "/courses",
        icon: MessageCircleQuestion,
        badge: `${managedHelpCount} 件`,
      },
    ];
  }

  return [
    {
      title: "整理教材",
      description: "上傳或查看文件處理狀態",
      to: "/documents",
      icon: FileText,
      primary: true,
    },
    {
      title: "問教材",
      description: "用個人或課程文件開始對話",
      to: "/chat",
      icon: MessageSquareText,
    },
    {
      title: "開始測驗",
      description: "從教材生成題目並練習",
      to: "/quiz/generate",
      icon: Layers3,
    },
    {
      title: "複習閃卡",
      description: "依間隔複習安排回想",
      to: "/flashcards?review=1",
      icon: BrainCircuit,
      badge: `${due} 張`,
    },
  ];
}

function QuickActionCard({ action }: { action: QuickAction }) {
  return (
    <Link
      to={action.to}
      className={[
        "group flex min-h-32 flex-col justify-between rounded-lg border p-4 shadow-sm transition",
        action.primary
          ? "border-indigo-200 bg-indigo-50 hover:border-indigo-300"
          : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div
          className={[
            "flex h-10 w-10 items-center justify-center rounded-lg",
            action.primary
              ? "bg-white text-indigo-700"
              : "bg-zinc-100 text-zinc-600",
          ].join(" ")}
        >
          <action.icon size={20} />
        </div>
        {action.badge && (
          <span className="rounded-md bg-white px-2 py-1 text-xs font-medium text-zinc-600 ring-1 ring-zinc-200">
            {action.badge}
          </span>
        )}
      </div>
      <div>
        <div className="text-sm font-semibold text-zinc-900">
          {action.title}
        </div>
        <div className="mt-1 text-xs leading-5 text-zinc-500">
          {action.description}
        </div>
      </div>
    </Link>
  );
}

function taskLabel(task: Record<string, any>) {
  if (task.type === "flashcard_review") return `複習 ${task.due_count} 張閃卡`;
  if (task.type === "read_summary") return "閱讀或生成摘要";
  if (task.type === "take_quiz")
    return `完成 ${task.suggested_count ?? 5} 題測驗`;
  return String(task.type);
}

function taskHref(task: Record<string, any>) {
  if (task.type === "flashcard_review") return "/flashcards?review=1";
  if (task.type === "read_summary" && task.doc_id)
    return `/summary/${task.doc_id}`;
  if (task.type === "take_quiz") {
    const docId = task.doc_id ?? task.suggested_doc_id;
    if (docId) return `/quiz/generate?doc=${docId}`;
  }
  return "/documents";
}

function helpStatusLabel(status: string) {
  if (status === "in_progress") return "處理中";
  if (status === "resolved") return "已結案";
  return "待處理";
}

function Metric({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: number;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm text-zinc-500">{title}</span>
        <Icon size={18} className="text-zinc-500" />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
