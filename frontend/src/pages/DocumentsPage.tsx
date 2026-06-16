import { ChangeEvent, useEffect, useState } from "react"
import { FileText, RefreshCw, Upload } from "lucide-react"
import { apiFetch, apiUpload, DocumentItem } from "../lib/api"
import { wsManager } from "../lib/ws"

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function loadDocuments() {
    const data = await apiFetch<DocumentItem[]>("/documents")
    setDocuments(data)
  }

  useEffect(() => {
    loadDocuments().catch(() => undefined)
    const token = localStorage.getItem("access_token")
    if (token) wsManager.connect(token)
    const offStatus = wsManager.on("doc_status", () => loadDocuments().catch(() => undefined))
    const offReady = wsManager.on("doc_ready", () => loadDocuments().catch(() => undefined))
    return () => {
      offStatus()
      offReady()
    }
  }, [])

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError("")
    try {
      await apiUpload<DocumentItem>("/documents/upload", file)
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : "上傳失敗")
    } finally {
      setLoading(false)
      event.target.value = ""
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">文件</h1>
          <p className="mt-1 text-sm text-zinc-500">PDF、Markdown、PPTX、DOCX</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
            onClick={() => loadDocuments()}
          >
            <RefreshCw size={16} />
            重新整理
          </button>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            <Upload size={16} />
            上傳
            <input className="hidden" type="file" accept=".pdf,.md,.pptx,.docx" onChange={onFile} />
          </label>
        </div>
      </div>
      {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
      <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="grid grid-cols-[1fr_120px_120px] border-b border-zinc-200 px-5 py-3 text-xs font-medium uppercase text-zinc-500">
          <div>名稱</div>
          <div>狀態</div>
          <div className="text-right">大小</div>
        </div>
        <div className="divide-y divide-zinc-100">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="grid grid-cols-[1fr_120px_120px] items-center px-5 py-4 text-sm"
            >
              <div className="flex min-w-0 items-center gap-3">
                <FileText size={18} className="shrink-0 text-zinc-500" />
                <div className="min-w-0">
                  <div className="truncate font-medium">{doc.filename}</div>
                  <div className="text-xs text-zinc-500">
                    {doc.page_count ?? 0} 頁 · {doc.chunk_count ?? 0} chunks
                  </div>
                </div>
              </div>
              <span className={statusClass(doc.status)}>{doc.status}</span>
              <div className="text-right text-zinc-500">{formatBytes(doc.file_size)}</div>
            </div>
          ))}
          {documents.length === 0 && (
            <div className="px-5 py-12 text-center text-sm text-zinc-500">
              {loading ? "上傳中" : "尚無文件"}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

function statusClass(status: string) {
  const base = "inline-flex w-fit rounded-lg px-2 py-1 text-xs"
  if (status === "ready") return `${base} bg-emerald-50 text-emerald-700`
  if (status === "error") return `${base} bg-red-50 text-red-600`
  return `${base} bg-indigo-50 text-indigo-700`
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

