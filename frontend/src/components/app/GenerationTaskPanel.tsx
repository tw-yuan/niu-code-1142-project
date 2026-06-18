import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import { GenerationTask } from "../../lib/api";

interface StatusProps {
  task: GenerationTask | null;
  error?: string;
  title: string;
  className?: string;
}

interface ListProps {
  tasks: GenerationTask[];
  emptyText?: string;
  showUser?: boolean;
}

export function GenerationTaskStatus({
  task,
  error,
  title,
  className = "",
}: StatusProps) {
  const [open, setOpen] = useState(false);
  if (!task && !error) return null;
  const progress = normalizeProgress(task);
  const active = task ? ["queued", "running"].includes(task.status) : false;

  return (
    <div
      className={[
        "mb-4 rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-indigo-800",
        className,
      ].join(" ")}
    >
      {task && (
        <>
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 text-left"
            onClick={() => setOpen((value) => !value)}
          >
            <span className="flex min-w-0 items-center gap-2">
              {active ? (
                <Loader2 size={16} className="shrink-0 animate-spin" />
              ) : task.status === "failed" ? (
                <AlertCircle size={16} className="shrink-0 text-red-600" />
              ) : (
                <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
              )}
              <span className="min-w-0 truncate">
                {title}：{taskProgressText(task)}
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-2 text-xs">
              {progress.percent}%
              {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </span>
          </button>
          <ProgressBar percent={progress.percent} className="mt-2" />
          {open && (
            <div className="mt-3 grid gap-2 rounded-md bg-white/70 p-3 text-xs text-zinc-600 sm:grid-cols-3">
              <Info label="狀態" value={statusLabel(task.status)} />
              <Info
                label="進度"
                value={`${progress.current} / ${progress.total}`}
              />
              <Info label="更新" value={shortDate(task.updated_at)} />
              {task.error && (
                <div className="sm:col-span-3 text-red-600">{task.error}</div>
              )}
            </div>
          )}
        </>
      )}
      {error && <div className="mt-2 text-red-600">{error}</div>}
    </div>
  );
}

export function GenerationTaskList({
  tasks,
  emptyText = "目前沒有任務",
  showUser = false,
}: ListProps) {
  if (tasks.length === 0) {
    return <div className="px-5 py-8 text-sm text-zinc-500">{emptyText}</div>;
  }
  return (
    <div className="divide-y divide-zinc-100">
      {tasks.map((task) => {
        const progress = normalizeProgress(task);
        return (
          <div key={task.id} className="px-5 py-3 text-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2 font-medium text-zinc-900">
                  <TaskIcon task={task} />
                  <span>{kindLabel(task.kind)}</span>
                  <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs font-normal text-zinc-600">
                    {statusLabel(task.status)}
                  </span>
                </div>
                <div className="mt-1 text-xs text-zinc-500">
                  {taskProgressText(task)}
                  {showUser && task.user
                    ? ` · ${task.user.username} (${task.user.email ?? task.user.id})`
                    : ""}
                </div>
              </div>
              <div className="w-full shrink-0 sm:w-40">
                <div className="mb-1 text-right text-xs text-zinc-500">
                  {progress.percent}%
                </div>
                <ProgressBar percent={progress.percent} />
              </div>
            </div>
            {task.error && (
              <div className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600">
                {task.error}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function TaskIcon({ task }: { task: GenerationTask }) {
  if (["queued", "running"].includes(task.status)) {
    return <Loader2 size={15} className="animate-spin text-indigo-600" />;
  }
  if (task.status === "failed") {
    return <AlertCircle size={15} className="text-red-600" />;
  }
  return <CheckCircle2 size={15} className="text-emerald-600" />;
}

function ProgressBar({
  percent,
  className = "",
}: {
  percent: number;
  className?: string;
}) {
  return (
    <div
      className={[
        "h-1.5 rounded-full bg-white ring-1 ring-zinc-200",
        className,
      ].join(" ")}
    >
      <div
        className="h-full rounded-full bg-indigo-600 transition-all"
        style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
      />
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-0.5 text-zinc-400">{label}</div>
      <div className="font-medium text-zinc-700">{value || "-"}</div>
    </div>
  );
}

function normalizeProgress(task: GenerationTask | null) {
  const total = Math.max(1, task?.progress?.total ?? 1);
  const current = Math.min(Math.max(0, task?.progress?.current ?? 0), total);
  const percent = Math.round(task?.progress?.percent ?? (current / total) * 100);
  return { current, total, percent };
}

function taskProgressText(task: GenerationTask) {
  return task.progress?.message || statusLabel(task.status);
}

function statusLabel(status: string) {
  if (status === "queued") return "排隊中";
  if (status === "running") return "執行中";
  if (status === "succeeded") return "完成";
  if (status === "failed") return "失敗";
  return status;
}

function kindLabel(kind: string) {
  if (kind === "quiz") return "測驗生成";
  if (kind === "flashcards") return "閃卡生成";
  if (kind === "mindmap") return "心智圖生成";
  return kind;
}

function shortDate(value: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  return date.toLocaleString(undefined, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
