import { useState } from 'react'
import type { AgentTraceInfo } from '../api/tasks'

type Props = {
  trace: AgentTraceInfo | null
  loading: boolean
  error: string | null
}

const TOOL_LABEL: Record<string, string> = {
  list_inputs: '列出輸入',
  read_input_text: '讀取文字',
  read_input_table: '讀取表格',
  log_progress: '進度訊息',
  add_reference: '新增引用',
  add_limitation: '新增限制',
  write_text_file: '寫純文字',
  write_docx_file: '寫 DOCX',
  write_pdf_file: '寫 PDF',
  write_xlsx_file: '寫 XLSX',
  finish: '結束任務',
}

export default function DetailedProcessPanel({ trace, loading, error }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <section className="rounded-2xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div>
          <h2 className="font-semibold">詳細處理過程</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            點此{open ? '收合' : '展開'} tool call 紀錄、引用與限制
          </p>
        </div>
        <span className="text-slate-400">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="border-t border-slate-200 p-5 space-y-6">
          {loading && <div className="text-sm text-slate-500">載入中…</div>}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          {trace && (
            <>
              <div>
                <h3 className="text-sm font-semibold mb-2 text-slate-700">Tool call timeline</h3>
                {trace.tool_calls.length === 0 && <div className="text-xs text-slate-500">尚無紀錄</div>}
                <ul className="space-y-1 text-xs font-mono">
                  {trace.tool_calls.map((c) => (
                    <li
                      key={c.id}
                      className={`px-2 py-1 rounded ${
                        c.status === 'error'
                          ? 'bg-red-50 text-red-700'
                          : c.status === 'ignored'
                            ? 'bg-slate-50 text-slate-500'
                            : 'bg-slate-50 text-slate-800'
                      }`}
                    >
                      <span className="text-slate-400">iter {c.iteration} · </span>
                      <span className="font-semibold">{TOOL_LABEL[c.tool_name] ?? c.tool_name}</span>
                      <span className="text-slate-400"> · {c.status}</span>
                      {c.duration_ms != null && <span className="text-slate-400"> · {c.duration_ms}ms</span>}
                      {c.error_message && <span className="text-red-600"> · {c.error_message}</span>}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2 text-slate-700">引用來源 ({trace.references.length})</h3>
                {trace.references.length === 0 ? (
                  <div className="text-xs text-slate-500">無</div>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {trace.references.map((r) => (
                      <li key={r.id} className="rounded border border-slate-200 p-2">
                        <div className="font-medium">{r.source_name}</div>
                        {r.quote_or_summary && <div className="text-xs text-slate-600 mt-1">{r.quote_or_summary}</div>}
                        {r.used_for && <div className="text-xs text-slate-500 mt-1">用於：{r.used_for}</div>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2 text-slate-700">限制與待確認 ({trace.limitations.length})</h3>
                {trace.limitations.length === 0 ? (
                  <div className="text-xs text-slate-500">無</div>
                ) : (
                  <ul className="space-y-1 text-sm list-disc list-inside text-slate-700">
                    {trace.limitations.map((l) => (
                      <li key={l.id}>{l.text}</li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  )
}
