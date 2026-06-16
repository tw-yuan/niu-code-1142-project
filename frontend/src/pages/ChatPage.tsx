import { FormEvent, useEffect, useMemo, useState } from "react"
import { MessageSquarePlus, Send, StopCircle } from "lucide-react"
import { apiFetch, ChatMessage, ChatSession, Citation, DocumentItem } from "../lib/api"
import { streamFetch } from "../lib/stream"

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [mode, setMode] = useState("enhanced")
  const [streaming, setStreaming] = useState(false)
  const [aborter, setAborter] = useState<AbortController | null>(null)

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeId),
    [sessions, activeId],
  )

  useEffect(() => {
    loadSessions().catch(() => undefined)
    apiFetch<DocumentItem[]>("/documents").then(setDocuments).catch(() => setDocuments([]))
  }, [])

  async function loadSessions() {
    const data = await apiFetch<ChatSession[]>("/chat/sessions")
    setSessions(data)
    if (!activeId && data[0]) {
      await openSession(data[0].id)
    }
  }

  async function openSession(id: string) {
    const detail = await apiFetch<ChatSession>(`/chat/sessions/${id}`)
    setActiveId(id)
    setMessages(detail.messages ?? [])
  }

  async function createSession() {
    const session = await apiFetch<ChatSession>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ doc_ids: selectedDocs, mode }),
    })
    setSessions((prev) => [session, ...prev])
    setActiveId(session.id)
    setMessages([])
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    if (!input.trim() || streaming) return
    let sessionId = activeId
    if (!sessionId) {
      const session = await apiFetch<ChatSession>("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ doc_ids: selectedDocs, mode }),
      })
      setSessions((prev) => [session, ...prev])
      sessionId = session.id
      setActiveId(session.id)
    }
    const question = input
    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "" }])
    const controller = new AbortController()
    setAborter(controller)
    setStreaming(true)
    let assistant = ""
    let citations: Citation[] = []
    try {
      for await (const event of streamFetch(
        `/chat/sessions/${sessionId}/message`,
        { content: question },
        controller.signal,
      )) {
        if (event.type === "chunk") {
          assistant += event.content
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = { role: "assistant", content: assistant, citations }
            return next
          })
        } else if (event.type === "citations") {
          citations = event.data
        } else if (event.type === "error") {
          assistant += `\n\n[錯誤：${event.message}]`
        }
      }
    } finally {
      setMessages((prev) => {
        const next = [...prev]
        if (next.length > 0 && next[next.length - 1].role === "assistant") {
          next[next.length - 1] = { role: "assistant", content: assistant, citations }
        }
        return next
      })
      setStreaming(false)
      setAborter(null)
      loadSessions().catch(() => undefined)
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-40px)] gap-4 lg:grid-cols-[280px_1fr]">
      <aside className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 p-4">
          <button
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            onClick={createSession}
          >
            <MessageSquarePlus size={16} />
            新對話
          </button>
        </div>
        <div className="border-b border-zinc-200 p-4">
          <label className="mb-2 block text-xs font-medium text-zinc-500">模式</label>
          <select
            className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            <option value="enhanced">增強</option>
            <option value="strict">嚴格</option>
            <option value="socratic">蘇格拉底</option>
          </select>
          <div className="space-y-2">
            {documents
              .filter((doc) => doc.status === "ready")
              .map((doc) => (
                <label key={doc.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedDocs.includes(doc.id)}
                    onChange={(event) => {
                      setSelectedDocs((prev) =>
                        event.target.checked
                          ? [...prev, doc.id]
                          : prev.filter((item) => item !== doc.id),
                      )
                    }}
                  />
                  <span className="truncate">{doc.filename}</span>
                </label>
              ))}
          </div>
        </div>
        <div className="max-h-[55vh] overflow-y-auto p-2 scrollbar-thin">
          {sessions.map((session) => (
            <button
              key={session.id}
              className={[
                "mb-1 block w-full truncate rounded-lg px-3 py-2 text-left text-sm",
                session.id === activeId ? "bg-indigo-50 text-indigo-700" : "hover:bg-zinc-100",
              ].join(" ")}
              onClick={() => openSession(session.id)}
            >
              {session.title || "新的對話"}
            </button>
          ))}
        </div>
      </aside>
      <section className="flex min-h-[calc(100vh-40px)] flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h1 className="font-semibold">{activeSession?.title || "RAG 對話"}</h1>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-5 scrollbar-thin">
          {messages.map((message, index) => (
            <div
              key={index}
              className={message.role === "user" ? "ml-auto max-w-2xl" : "mr-auto max-w-3xl"}
            >
              <div
                className={[
                  "rounded-lg px-4 py-3 text-sm leading-7",
                  message.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "border border-zinc-200 bg-zinc-50 text-zinc-900",
                ].join(" ")}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
              </div>
              {message.citations && message.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-500">
                  {message.citations.map((citation) => (
                    <span key={`${citation.doc_id}-${citation.chunk_index}`} className="rounded-lg bg-zinc-100 px-2 py-1">
                      [{citation.index}] {citation.filename} p.{citation.page}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <form onSubmit={sendMessage} className="border-t border-zinc-200 p-4">
          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-600"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="輸入問題"
            />
            {streaming ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                onClick={() => aborter?.abort()}
              >
                <StopCircle size={16} />
                停止
              </button>
            ) : (
              <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                <Send size={16} />
                送出
              </button>
            )}
          </div>
        </form>
      </section>
    </div>
  )
}
