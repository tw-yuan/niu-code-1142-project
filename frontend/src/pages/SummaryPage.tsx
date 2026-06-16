import { useEffect, useState } from "react"
import { FileText, Wand2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { useParams } from "react-router-dom"
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge"
import { apiFetch, DocumentItem } from "../lib/api"
import { streamFetch } from "../lib/stream"
import { useAuthStore } from "../store/auth"

export function SummaryPage() {
  const { docId } = useParams()
  const user = useAuthStore((state) => state.user)
  const [doc, setDoc] = useState<DocumentItem | null>(null)
  const [kind, setKind] = useState<"full" | "bullets">("full")
  const [content, setContent] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!docId) return
    apiFetch<DocumentItem>(`/documents/${docId}`).then(setDoc).catch(() => undefined)
    apiFetch<{ content: string }>(`/summary/${docId}`).then((data) => setContent(data.content)).catch(() => undefined)
  }, [docId])

  async function generate() {
    if (!docId || user?.quota_status === "exceeded") return
    setStreaming(true)
    setError("")
    setContent("")
    let next = ""
    try {
      for await (const event of streamFetch("/summary/stream", { doc_id: docId, kind, count: 10 })) {
        if (event.type === "chunk") {
          next += event.content
          setContent(next)
        } else if (event.type === "error") {
          setError(event.message)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "摘要生成失敗")
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">摘要</h1>
          <p className="mt-1 text-sm text-zinc-500">{doc?.filename ?? "選定文件"}</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={kind} onChange={(event) => setKind(event.target.value as "full" | "bullets")}>
            <option value="full">完整摘要</option>
            <option value="bullets">重點條列</option>
          </select>
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            onClick={generate}
            disabled={streaming || user?.quota_status === "exceeded"}
          >
            <Wand2 size={16} />
            {streaming ? "生成中" : "生成摘要"}
          </button>
        </div>
      </div>
      <AIGeneratedBadge />
      {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        {content ? (
          <div className="prose prose-zinc max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <FileText size={16} />
            尚無摘要
          </div>
        )}
      </section>
    </div>
  )
}
