import type { ProgressEventInfo } from '../api/tasks'

type Props = {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  events: ProgressEventInfo[]
  iterationsUsed: number
  connected: boolean
}

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '處理中',
  completed: '已完成',
  failed: '失敗',
}

const EVENT_LABEL: Record<string, string> = {
  agent_start: 'Agent 啟動',
  agent_log: 'Agent 進度',
  agent_write: '寫入檔案',
  agent_text: 'Agent 文字回應',
  agent_finish: '完成',
  error: '錯誤',
}

export default function ProgressPanel({ status, events, iterationsUsed, connected }: Props) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold">即時進度</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            狀態 <span className="font-medium text-slate-700">{STATUS_LABEL[status] ?? status}</span>
            　·　迭代 {iterationsUsed}
            {status === 'processing' && (
              <span className={`ml-2 ${connected ? 'text-emerald-600' : 'text-amber-600'}`}>
                ● SSE {connected ? '已連線' : '連線中…'}
              </span>
            )}
          </p>
        </div>
        {status === 'processing' && (
          <div className="h-2 w-32 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-blue-500" />
          </div>
        )}
      </header>

      {events.length === 0 ? (
        <div className="text-sm text-slate-500">
          {status === 'pending' ? '尚未開始' : '等待第一筆進度訊息…'}
        </div>
      ) : (
        <ol className="space-y-2">
          {events.map((e) => (
            <li
              key={e.id}
              className={`rounded-lg border px-3 py-2 text-sm ${
                e.event_type === 'error'
                  ? 'border-red-200 bg-red-50 text-red-800'
                  : e.event_type === 'agent_finish'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                    : 'border-slate-200 bg-slate-50 text-slate-700'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-slate-500">
                  {EVENT_LABEL[e.event_type] ?? e.event_type}
                </span>
                <span className="text-[10px] text-slate-400">
                  {new Date(e.created_at).toLocaleTimeString('zh-TW')}
                </span>
              </div>
              <div>{e.message}</div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
