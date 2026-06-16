import { FormEvent, useEffect, useState } from "react"
import { Download, NotebookPen, Plus } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { BASE_URL, apiFetch, DocumentItem, NoteItem } from "../lib/api"

export function NotesPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [notes, setNotes] = useState<NoteItem[]>([])
  const [docId, setDocId] = useState("")
  const [content, setContent] = useState("")
  const [q, setQ] = useState("")

  async function load() {
    const [docs, nextNotes] = await Promise.all([
      apiFetch<DocumentItem[]>("/documents"),
      apiFetch<NoteItem[]>(`/notes${queryString({ doc_id: docId, q })}`),
    ])
    setDocuments(docs)
    setNotes(nextNotes)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [docId, q])

  async function create(event: FormEvent) {
    event.preventDefault()
    if (!content.trim()) return
    await apiFetch("/notes", {
      method: "POST",
      body: JSON.stringify({ content, doc_id: docId || null, source_type: "manual" }),
    })
    setContent("")
    await load()
  }

  async function deleteNote(id: string) {
    await apiFetch(`/notes/${id}`, { method: "DELETE" })
    await load()
  }

  function exportHref() {
    const token = encodeURIComponent(localStorage.getItem("access_token") ?? "")
    return docId ? `${BASE_URL}/notes/export/${docId}?token=${token}` : "#"
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">筆記</h1>
          <p className="mt-1 text-sm text-zinc-500">保存 AI 回應、摘要與自己的理解</p>
        </div>
        <a className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 aria-disabled:pointer-events-none aria-disabled:opacity-50" href={exportHref()} aria-disabled={!docId}>
          <Download size={16} />
          匯出 Markdown
        </a>
      </div>
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <form className="space-y-3" onSubmit={create}>
            <select className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={docId} onChange={(event) => setDocId(event.target.value)}>
              <option value="">全部文件</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>{doc.filename}</option>
              ))}
            </select>
            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={q} onChange={(event) => setQ(event.target.value)} placeholder="搜尋筆記" />
            <textarea className="min-h-40 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={content} onChange={(event) => setContent(event.target.value)} placeholder="新增 Markdown 筆記" />
            <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
              <Plus size={16} />
              新增
            </button>
          </form>
        </aside>
        <section className="space-y-3">
          {notes.map((note) => (
            <article key={note.id} className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <NotebookPen size={16} />
                  {note.source_type ?? "manual"} {note.source_page ? `· 第 ${note.source_page} 頁` : ""}
                </div>
                <button className="text-xs text-red-600" onClick={() => deleteNote(note.id)}>刪除</button>
              </div>
              <div className="prose prose-zinc max-w-none text-sm">
                <ReactMarkdown>{note.content}</ReactMarkdown>
              </div>
            </article>
          ))}
          {notes.length === 0 && <div className="rounded-lg border border-zinc-200 bg-white p-8 text-sm text-zinc-500">尚無筆記</div>}
        </section>
      </div>
    </div>
  )
}

function queryString(params: Record<string, string>) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value)
  })
  const text = search.toString()
  return text ? `?${text}` : ""
}
