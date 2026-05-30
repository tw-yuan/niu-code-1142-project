import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import ProgressPanel from '../components/ProgressPanel'
import DetailedProcessPanel from '../components/DetailedProcessPanel'
import ResultViewer from '../components/ResultViewer'
import { getAgentTrace, getTask, type AgentTraceInfo, type TaskInfo } from '../api/tasks'
import { ApiError } from '../api/client'
import { formatBytes, parseStatusLabel } from '../utils/format'
import { useTaskEvents } from '../hooks/useTaskEvents'

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [trace, setTrace] = useState<AgentTraceInfo | null>(null)
  const [traceLoading, setTraceLoading] = useState(false)
  const [traceError, setTraceError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!taskId) return
    try {
      const data = await getTask(taskId)
      setTask(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : '載入任務失敗')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    refresh()
  }, [refresh])

  // SSE for progress while processing
  const onTerminal = useCallback(() => {
    refresh()
  }, [refresh])
  const { events, connected } = useTaskEvents({
    enabled: task?.status === 'processing' || task?.status === 'pending',
    taskId,
    onTerminal,
  })

  // Polling fallback: every 8s while processing, also refresh in case SSE missed something
  useEffect(() => {
    if (task?.status !== 'processing' && task?.status !== 'pending') return
    const timer = window.setInterval(() => refresh(), 8000)
    return () => window.clearInterval(timer)
  }, [task?.status, refresh])

  // Load trace lazily once completed/failed (or on demand)
  useEffect(() => {
    if (!taskId) return
    if (task?.status === 'completed' || task?.status === 'failed') {
      setTraceLoading(true)
      setTraceError(null)
      getAgentTrace(taskId)
        .then((t) => setTrace(t))
        .catch((e) => setTraceError(e instanceof ApiError ? e.detail : '載入詳細過程失敗'))
        .finally(() => setTraceLoading(false))
    }
  }, [taskId, task?.status])

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">任務詳情</h1>
          <Link to="/app" className="text-sm text-blue-600 hover:underline">+ 新任務</Link>
        </div>

        {loading && <div className="text-slate-500 text-sm">載入中…</div>}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        {task && (
          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs text-slate-500">任務 ID</span>
                <span className="font-mono text-xs text-slate-700 break-all">{task.id}</span>
                {task.model_name && (
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    模型 {task.model_name}
                  </span>
                )}
              </div>
              {task.assignment_text && (
                <>
                  <div className="text-xs text-slate-500 pt-1">作業敘述</div>
                  <pre className="whitespace-pre-wrap text-sm text-slate-800">{task.assignment_text}</pre>
                </>
              )}
            </section>

            <ProgressPanel
              status={task.status}
              events={events}
              iterationsUsed={task.iterations_used}
              connected={connected}
            />

            <ResultViewer task={task} />

            <DetailedProcessPanel
              trace={trace}
              loading={traceLoading}
              error={traceError}
            />

            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="font-semibold">上傳檔案</h2>
              {task.files.length === 0 && <div className="text-sm text-slate-500">未上傳任何檔案。</div>}
              {task.files.length > 0 && (
                <ul className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
                  {task.files.map((f) => (
                    <li key={f.id} className="p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-slate-800">{f.original_filename}</div>
                        <span className="text-xs text-slate-500">
                          {f.file_category === 'course_material' ? '課程資料' : '作業檔案'} · {f.file_type} · {formatBytes(f.file_size)}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        解析：<span className={f.parse_status === 'success' ? 'text-emerald-600' : 'text-amber-600'}>
                          {parseStatusLabel(f.parse_status)}
                        </span>
                        {f.error_message && <span className="ml-2 text-red-600">{f.error_message}</span>}
                      </div>
                      {f.summary && (
                        <div className="text-xs text-slate-600 mt-1 line-clamp-3 whitespace-pre-wrap">
                          {f.summary}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
