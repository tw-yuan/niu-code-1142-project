import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { useSession } from '../auth/SessionContext'
import { deleteTask, listHistory, type HistoryItem } from '../api/history'
import { ApiError } from '../api/client'
import { formatRelative } from '../utils/format'

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-700',
  processing: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '處理中',
  completed: '已完成',
  failed: '失敗',
}

export default function HistoryPage() {
  const { session } = useSession()
  const isAdmin = session?.role === 'admin'
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listHistory()
      setItems(data)
      setError(null)
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleDelete(taskId: string) {
    if (!confirm('確定刪除此任務？這會一併移除上傳檔案與 Agent 產出。')) return
    setDeletingId(taskId)
    try {
      await deleteTask(taskId)
      setItems((prev) => prev.filter((t) => t.id !== taskId))
    } catch (e) {
      alert(e instanceof ApiError ? e.detail : '刪除失敗')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">歷史紀錄</h1>
          {!isAdmin && (
            <Link to="/app" className="text-sm text-blue-600 hover:underline">+ 新任務</Link>
          )}
        </div>

        {loading && <div className="text-slate-500 text-sm">載入中…</div>}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        {!loading && items.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            目前尚無任務紀錄。
          </div>
        )}

        {items.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">標題 / 摘要</th>
                  {isAdmin && <th className="text-left px-4 py-3">使用者</th>}
                  <th className="text-left px-4 py-3">狀態</th>
                  <th className="text-left px-4 py-3">迭代</th>
                  <th className="text-left px-4 py-3">建立</th>
                  <th className="text-right px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 max-w-md">
                      <div className="font-medium text-slate-800 truncate">
                        {t.agent_title ?? '（未命名任務）'}
                      </div>
                      <div className="text-xs text-slate-500 truncate">
                        {t.assignment_text || '（無作業敘述）'}
                      </div>
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-slate-700">{t.owner_display_name ?? '—'}</td>
                    )}
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${STATUS_STYLE[t.status] ?? 'bg-slate-100'}`}>
                        {STATUS_LABEL[t.status] ?? t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{t.iterations_used}</td>
                    <td className="px-4 py-3 text-slate-500">{formatRelative(t.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Link
                          to={`/tasks/${t.id}`}
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                        >
                          查看
                        </Link>
                        {!isAdmin && (
                          <button
                            type="button"
                            onClick={() => handleDelete(t.id)}
                            disabled={deletingId === t.id}
                            className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            {deletingId === t.id ? '刪除中…' : '刪除'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
