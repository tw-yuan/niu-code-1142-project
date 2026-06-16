import { useEffect, useState } from "react"
import { GitBranch, Wand2 } from "lucide-react"
import { useParams } from "react-router-dom"
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge"
import { MarkdownContent } from "../components/app/MarkdownContent"
import { apiFetch, DocumentItem } from "../lib/api"
import { streamFetch } from "../lib/stream"
import { useAuthStore } from "../store/auth"

export function MindmapPage() {
  const { docId } = useParams()
  const user = useAuthStore((state) => state.user)
  const [doc, setDoc] = useState<DocumentItem | null>(null)
  const [content, setContent] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!docId) return
    apiFetch<DocumentItem>(`/documents/${docId}`).then(setDoc).catch(() => undefined)
    apiFetch<{ content: string }>(`/mindmap/${docId}`).then((data) => setContent(data.content)).catch(() => undefined)
  }, [docId])

  async function generate() {
    if (!docId || user?.quota_status === "exceeded") return
    setStreaming(true)
    setError("")
    setContent("")
    let next = ""
    try {
      for await (const event of streamFetch("/mindmap/stream", { doc_id: docId })) {
        if (event.type === "chunk") {
          next += event.content
          setContent(next)
        } else if (event.type === "error") {
          setError(event.message)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "心智圖生成失敗")
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">心智圖</h1>
          <p className="mt-1 text-sm text-zinc-500">{doc?.filename ?? "選定文件"}</p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          onClick={generate}
          disabled={streaming || user?.quota_status === "exceeded"}
        >
          <Wand2 size={16} />
          {streaming ? "生成中" : "生成心智圖"}
        </button>
      </div>
      <AIGeneratedBadge />
      {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        {content ? (
          <MarkdownContent>{content}</MarkdownContent>
        ) : (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <GitBranch size={16} />
            尚無心智圖
          </div>
        )}
      </section>
    </div>
  )
}
