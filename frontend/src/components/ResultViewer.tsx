import { useState } from 'react'
import type { GeneratedFileInfo, TaskInfo } from '../api/tasks'
import { generatedFileDownloadUrl } from '../api/tasks'
import { formatBytes } from '../utils/format'

type Props = {
  task: TaskInfo
}

const FORMAT_LABEL: Record<string, string> = {
  txt: '純文字',
  md: 'Markdown',
  docx: 'Word',
  pdf: 'PDF',
  xlsx: 'Excel',
}

export default function ResultViewer({ task }: Props) {
  if (task.status !== 'completed' && !task.agent_explanation) {
    if (task.status === 'failed') {
      return (
        <section className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <h2 className="font-semibold text-red-800">Agent 未能完成任務</h2>
          {task.error_message && <p className="text-sm text-red-700 mt-2">{task.error_message}</p>}
          {task.generated_files.length > 0 && (
            <p className="text-xs text-red-700 mt-2">
              已寫出 {task.generated_files.length} 份檔案，可從下方下載。
            </p>
          )}
        </section>
      )
    }
    return null
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
      <header>
        <h2 className="font-semibold">Agent 結果</h2>
        {task.agent_title && <p className="text-lg font-bold mt-1">{task.agent_title}</p>}
        {task.agent_assignment_summary && (
          <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">{task.agent_assignment_summary}</p>
        )}
      </header>

      {task.agent_explanation && (
        <ExplanationBlock text={task.agent_explanation} />
      )}

      {task.generated_files.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">下載檔案</h3>
          <ul className="space-y-2">
            {task.generated_files.map((g) => (
              <DownloadRow key={g.id} task={task} gf={g} />
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function ExplanationBlock({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore */
    }
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500">Agent 講解</span>
        <button
          type="button"
          onClick={copy}
          className="rounded-md border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
        >
          {copied ? '已複製' : '複製文字'}
        </button>
      </div>
      <pre className="whitespace-pre-wrap text-sm text-slate-800 font-sans">{text}</pre>
    </div>
  )
}

function DownloadRow({ task, gf }: { task: TaskInfo; gf: GeneratedFileInfo }) {
  return (
    <li className="rounded-lg border border-slate-200 px-3 py-2 flex items-center justify-between">
      <div>
        <div className="text-sm font-medium text-slate-800">{gf.filename}</div>
        <div className="text-xs text-slate-500">
          <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 mr-2">
            {FORMAT_LABEL[gf.format] ?? gf.format.toUpperCase()}
          </span>
          {formatBytes(gf.size_bytes)}
          {gf.purpose && <span className="ml-2 text-slate-400">· {gf.purpose}</span>}
        </div>
      </div>
      <a
        href={generatedFileDownloadUrl(task.id, gf.id)}
        download={gf.filename}
        className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
      >
        下載
      </a>
    </li>
  )
}
