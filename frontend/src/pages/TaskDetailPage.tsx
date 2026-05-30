import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { getTask, type TaskInfo } from '../api/tasks'
import { ApiError } from '../api/client'
import { formatBytes, parseStatusLabel } from '../utils/format'

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!taskId) return
    let cancelled = false
    setLoading(true)
    getTask(taskId)
      .then((t) => {
        if (!cancelled) setTask(t)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e instanceof ApiError ? e.detail : '載入任務失敗')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [taskId])

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
              <div className="text-xs text-slate-500">任務 ID</div>
              <div className="font-mono text-xs text-slate-700 break-all">{task.id}</div>
              <div className="text-xs text-slate-500 pt-2">狀態</div>
              <div>
                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                  {task.status}
                </span>
              </div>
              {task.assignment_text && (
                <>
                  <div className="text-xs text-slate-500 pt-2">作業敘述</div>
                  <pre className="whitespace-pre-wrap text-sm text-slate-800">{task.assignment_text}</pre>
                </>
              )}
            </section>

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

            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="font-semibold">下一步</h2>
              <p className="text-sm text-slate-500 mt-1">
                M5 後會在這裡顯示 Agent 即時進度、tool call trace 與下載檔案。
              </p>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
