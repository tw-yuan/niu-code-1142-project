import { useState } from 'react'
import { runTask, type TaskInfo } from '../api/tasks'
import { ApiError } from '../api/client'

type Props = {
  task: TaskInfo
  onStarted: () => void
}

export default function RerunPanel({ task, onStarted }: Props) {
  const [open, setOpen] = useState(false)
  const [model, setModel] = useState(task.model_name ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onRerun() {
    setError(null)
    setSubmitting(true)
    try {
      await runTask(task.id, model.trim() ? { model_name: model.trim() } : {})
      setOpen(false)
      onStarted()
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : '重新執行失敗')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold">重新執行</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            使用相同的上傳檔案與作業敘述重新跑一次。Agent 上一次寫出的檔案、tool call 與引用會被清空。
          </p>
        </div>
        {!open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
          >
            重新執行 / 換模型
          </button>
        )}
      </header>

      {open && (
        <div className="space-y-3 pt-2 border-t border-slate-100">
          <label className="block text-sm">
            <span className="text-slate-700">模型（選填）</span>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="留空使用後台預設值，例如 openai/gpt-5-mini"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="block text-xs text-slate-500 mt-1">
              覆寫只影響本次執行，不會修改後台預設模型。
            </span>
          </label>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setOpen(false)
                setError(null)
                setModel(task.model_name ?? '')
              }}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="button"
              onClick={onRerun}
              disabled={submitting}
              className="rounded-lg bg-blue-600 text-white px-4 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:bg-slate-300"
            >
              {submitting ? '啟動中…' : '開始重新執行'}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
