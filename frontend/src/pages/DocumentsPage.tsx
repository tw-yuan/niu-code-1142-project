import { ChangeEvent, useEffect, useState } from "react"
import { BookOpenCheck, FileText, MessageSquareText, RefreshCw, Trash2, Upload } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { BASE_URL, apiFetch, apiUpload, DocumentItem } from "../lib/api"
import { wsManager } from "../lib/ws"

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selected, setSelected] = useState<DocumentItem | null>(null)
  const [coverage, setCoverage] = useState<{ chapters: CoverageChapter[] }>({ chapters: [] })
  const [consented, setConsented] = useState(false)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const { id } = useParams()
  const navigate = useNavigate()

  async function loadDocuments() {
    const data = await apiFetch<DocumentItem[]>("/documents")
    setDocuments(data)
    const active = id ? data.find((doc) => doc.id === id) : null
    setSelected(active ?? data[0] ?? null)
  }

  useEffect(() => {
    loadDocuments().catch(() => undefined)
    apiFetch<Array<{ consent_type: string }>>("/legal/consents")
      .then((items) => setConsented(items.some((item) => item.consent_type === "copyright_declaration")))
      .catch(() => undefined)
    const token = localStorage.getItem("access_token")
    if (token) wsManager.connect(token)
    const offStatus = wsManager.on("doc_status", () => loadDocuments().catch(() => undefined))
    const offReady = wsManager.on("doc_ready", () => loadDocuments().catch(() => undefined))
    return () => {
      offStatus()
      offReady()
    }
  }, [id])

  useEffect(() => {
    if (!selected) return
    apiFetch<{ chapters: CoverageChapter[] }>(`/documents/${selected.id}/coverage`)
      .then(setCoverage)
      .catch(() => setCoverage({ chapters: [] }))
  }, [selected])

  async function uploadFile(file: File) {
    setLoading(true)
    setError("")
    try {
      await apiUpload<DocumentItem>("/documents/upload", file)
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : "上傳失敗")
    } finally {
      setLoading(false)
      setPendingFile(null)
    }
  }

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!consented) {
      setPendingFile(file)
    } else {
      uploadFile(file).catch(() => undefined)
    }
    event.target.value = ""
  }

  async function acceptConsentAndUpload() {
    await apiFetch("/legal/consent", {
      method: "POST",
      body: JSON.stringify({ consent_type: "copyright_declaration" }),
    })
    setConsented(true)
    if (pendingFile) await uploadFile(pendingFile)
  }

  async function deleteDocument(docId: string) {
    if (!window.confirm("確定刪除此文件與向量資料？")) return
    await apiFetch(`/documents/${docId}`, { method: "DELETE" })
    if (selected?.id === docId) {
      setSelected(null)
      navigate("/documents")
    }
    await loadDocuments()
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
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="grid grid-cols-[1fr_120px_120px] border-b border-zinc-200 px-5 py-3 text-xs font-medium uppercase text-zinc-500">
          <div>名稱</div>
          <div>狀態</div>
          <div className="text-right">大小</div>
        </div>
        <div className="divide-y divide-zinc-100">
          {documents.map((doc) => (
            <button
              key={doc.id}
              className="grid w-full grid-cols-[1fr_120px_120px] items-center px-5 py-4 text-left text-sm hover:bg-zinc-50"
              onClick={() => {
                setSelected(doc)
                navigate(`/documents/${doc.id}`)
              }}
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
            </button>
          ))}
          {documents.length === 0 && (
            <div className="px-5 py-12 text-center text-sm text-zinc-500">
              {loading ? "上傳中" : "尚無文件"}
            </div>
          )}
        </div>
      </section>
      <aside className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        {selected ? (
          <div>
            <div className="border-b border-zinc-200 p-5">
              <div className="text-sm font-semibold">{selected.filename}</div>
              <div className="mt-1 text-xs text-zinc-500">{selected.page_count ?? 0} 頁 · {selected.chunk_count ?? 0} chunks</div>
            </div>
            <div className="space-y-3 p-5">
              {selected.status === "ready" && (
                <div className="flex flex-wrap gap-2">
                  <Link className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50" to={`/summary/${selected.id}`}>
                    <BookOpenCheck size={16} />
                    摘要
                  </Link>
                  <Link className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50" to={`/mindmap/${selected.id}`}>
                    心智圖
                  </Link>
                  <Link className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50" to="/chat">
                    <MessageSquareText size={16} />
                    對話
                  </Link>
                </div>
              )}
              {selected.status === "error" && selected.error_msg && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{selected.error_msg}</div>
              )}
              {selected.page_count ? (
                <img
                  className="aspect-[3/4] w-full rounded-md border border-zinc-200 object-contain"
                  src={`${BASE_URL}/documents/${selected.id}/pages/1?token=${encodeURIComponent(localStorage.getItem("access_token") ?? "")}`}
                  alt="文件第一頁預覽"
                />
              ) : (
                <div className="rounded-md border border-dashed border-zinc-200 p-6 text-center text-sm text-zinc-500">尚無頁面預覽</div>
              )}
              <div>
                <div className="mb-2 text-sm font-medium">學習覆蓋度</div>
                <div className="space-y-2">
                  {coverage.chapters.map((chapter) => (
                    <div key={chapter.title}>
                      <div className="mb-1 flex justify-between text-xs text-zinc-500">
                        <span>{chapter.title}</span>
                        <span>{Math.round(chapter.coverage_score * 100)}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-zinc-100">
                        <div className="h-2 rounded-full bg-indigo-600" style={{ width: `${Math.round(chapter.coverage_score * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                  {coverage.chapters.length === 0 && <div className="text-sm text-zinc-500">尚無學習記錄</div>}
                </div>
              </div>
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                onClick={() => deleteDocument(selected.id)}
              >
                <Trash2 size={16} />
                刪除文件
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6 text-sm text-zinc-500">選擇文件查看詳情</div>
        )}
      </aside>
      </div>
      {pendingFile && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-zinc-950/30 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-lg font-semibold">上傳前著作權聲明</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-600">
              您上傳的文件必須為您合法持有的資料，或已獲得著作權人授權。本平台僅供個人學習使用，違反著作權法的責任由上傳者自行承擔。
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" onClick={() => setPendingFile(null)}>取消</button>
              <button className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white" onClick={acceptConsentAndUpload}>我已了解並同意</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface CoverageChapter {
  title: string
  page_range: [number, number]
  quiz_attempts: number
  quiz_score_avg: number
  flashcard_count: number
  flashcard_mastered: number
  chat_mentions: number
  coverage_score: number
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
