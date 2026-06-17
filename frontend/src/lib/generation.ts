import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, GenerationTask } from "./api";
import { wsManager } from "./ws";

export function useGenerationTask<TOutput = Record<string, unknown>>(
  kind: string,
  onSuccess?: (task: GenerationTask<TOutput>) => void | Promise<void>,
  matchTask?: (task: GenerationTask<TOutput>) => boolean,
) {
  const [task, setTask] = useState<GenerationTask<TOutput> | null>(null);
  const [error, setError] = useState("");
  const onSuccessRef = useRef(onSuccess);
  const matchTaskRef = useRef(matchTask);
  const completedRef = useRef(new Set<string>());

  useEffect(() => {
    onSuccessRef.current = onSuccess;
  }, [onSuccess]);

  useEffect(() => {
    matchTaskRef.current = matchTask;
  }, [matchTask]);

  const refreshActiveTask = useCallback(async () => {
    const tasks = await apiFetch<GenerationTask<TOutput>[]>(
      `/generation/tasks?kind=${encodeURIComponent(kind)}`,
    );
    setTask(tasks.find((item) => matchTaskRef.current?.(item) ?? true) ?? null);
  }, [kind]);

  const handleTaskUpdate = useCallback(async (taskId: string) => {
    const next = await apiFetch<GenerationTask<TOutput>>(
      `/generation/tasks/${taskId}`,
    );
    if (!(matchTaskRef.current?.(next) ?? true)) return;
    setTask(next);
    if (next.status === "succeeded") {
      if (!completedRef.current.has(next.id)) {
        completedRef.current.add(next.id);
        await onSuccessRef.current?.(next);
      }
    } else if (next.status === "failed") {
      setError(next.error ?? "生成失敗");
    }
  }, []);

  useEffect(() => {
    refreshActiveTask().catch(() => undefined);
  }, [refreshActiveTask]);

  useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    let stopped = false;
    const timer = window.setInterval(async () => {
      try {
        if (stopped) return;
        await handleTaskUpdate(task.id);
      } catch (err) {
        if (!stopped) {
          setError(err instanceof Error ? err.message : "任務狀態載入失敗");
        }
      }
    }, 2000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [handleTaskUpdate, task]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) wsManager.connect(token);
    const off = wsManager.on(
      "generation_task",
      (message: { task_id?: string; kind?: string }) => {
        if (message.kind !== kind || !message.task_id) return;
        handleTaskUpdate(message.task_id).catch((err) => {
          setError(err instanceof Error ? err.message : "任務狀態載入失敗");
        });
      },
    );
    return () => {
      off();
    };
  }, [handleTaskUpdate, kind]);

  function watch(
    nextTask: GenerationTask<TOutput> | { task_id: string; status: string },
  ) {
    setError("");
    if (!("task_id" in nextTask)) {
      setTask(nextTask);
      return;
    }
    setTask({
      id: nextTask.task_id,
      kind,
      status: nextTask.status,
      input: {},
      output: null,
      error: null,
      artifact_id: null,
      created_at: "",
      updated_at: "",
      finished_at: null,
    });
  }

  const active = Boolean(task && ["queued", "running"].includes(task.status));

  return {
    active,
    error,
    task,
    watch,
    refreshActiveTask,
  };
}
