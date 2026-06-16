import { FormEvent, useEffect, useMemo, useState } from "react"
import { BrainCircuit, Plus, Trash2, Wand2 } from "lucide-react"
import { useLocation } from "react-router-dom"
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge"
import { LoadingButton } from "../components/app/LoadingButton"
import { apiFetch, DocumentItem, FlashcardItem } from "../lib/api"
import { streamFetch } from "../lib/stream"
import { useAuthStore } from "../store/auth"

export function FlashcardsPage() {
  const user = useAuthStore((state) => state.user)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [cards, setCards] = useState<FlashcardItem[]>([])
  const [docId, setDocId] = useState("")
  const [front, setFront] = useState("")
  const [back, setBack] = useState("")
  const [preview, setPreview] = useState("")
  const [error, setError] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [creating, setCreating] = useState(false)
  const [reviewingCardId, setReviewingCardId] = useState<string | null>(null)
  const [deletingCardId, setDeletingCardId] = useState<string | null>(null)
  const [reviewMode, setReviewMode] = useState(false)
  const [reviewIndex, setReviewIndex] = useState(0)
  const [reviewed, setReviewed] = useState(0)
  const [remembered, setRemembered] = useState(0)
  const location = useLocation()

  const dueCards = useMemo(() => {
    const now = new Date().toISOString()
    return cards.filter((card) => card.next_review <= now)
  }, [cards])

  async function load() {
    const [docs, nextCards] = await Promise.all([
      apiFetch<DocumentItem[]>("/documents"),
      apiFetch<FlashcardItem[]>("/flashcards"),
    ])
    const ready = docs.filter((doc) => doc.status === "ready")
    setDocuments(ready)
    setCards(nextCards)
    if (!docId && ready[0]) setDocId(ready[0].id)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const doc = params.get("doc")
    if (doc) setDocId(doc)
    if (params.get("review") === "1") setReviewMode(true)
  }, [location.search])

  async function generate() {
    if (!docId || user?.quota_status === "exceeded") return
    setStreaming(true)
    setError("")
    setPreview("")
    let next = ""
    let failed = false
    try {
      for await (const event of streamFetch("/flashcards/stream", { doc_id: docId, count: 10 })) {
        if (event.type === "chunk") {
          next += event.content
          setPreview(next)
        } else if (event.type === "error") {
          failed = true
          setError(event.message)
        }
      }
      if (!failed) await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "閃卡生成失敗")
    } finally {
      setStreaming(false)
    }
  }

  async function createManual(event: FormEvent) {
    event.preventDefault()
    if (!front.trim() || !back.trim()) return
    setCreating(true)
    try {
      await apiFetch("/flashcards", {
        method: "POST",
        body: JSON.stringify({ front, back, doc_id: docId || null }),
      })
      setFront("")
      setBack("")
      await load()
    } finally {
      setCreating(false)
    }
  }

  async function review(cardId: string, quality: number) {
    setReviewingCardId(cardId)
    try {
      await apiFetch(`/flashcards/${cardId}/review`, {
        method: "POST",
        body: JSON.stringify({ quality }),
      })
      setReviewed((prev) => prev + 1)
      if (quality >= 3) setRemembered((prev) => prev + 1)
      setReviewIndex((prev) => prev + 1)
      await load()
    } finally {
      setReviewingCardId(null)
    }
  }

  async function deleteCard(card: FlashcardItem) {
    setDeletingCardId(card.id)
    try {
      await apiFetch(`/flashcards/${card.id}`, { method: "DELETE" })
      await load()
    } finally {
      setDeletingCardId(null)
    }
  }

  const activeReviewCard = dueCards[reviewIndex]

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">閃卡</h1>
        <p className="mt-1 text-sm text-zinc-500">待複習 {dueCards.length} 張</p>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <button className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-zinc-300" onClick={() => {
          setReviewMode(true)
          setReviewIndex(0)
          setReviewed(0)
          setRemembered(0)
        }} disabled={dueCards.length === 0}>
          開始今日複習
        </button>
        {reviewMode && (
          <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50" onClick={() => setReviewMode(false)}>
            回到列表
          </button>
        )}
      </div>
      {reviewMode && (
        <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          {activeReviewCard ? (
            <div>
              <div className="mb-2 text-xs text-zinc-500">第 {reviewIndex + 1} / {dueCards.length} 張</div>
              <div className="text-lg font-semibold">{activeReviewCard.front}</div>
              <div className="mt-4 whitespace-pre-wrap rounded-lg bg-zinc-50 p-4 text-sm leading-6 text-zinc-700">{activeReviewCard.back}</div>
              <div className="mt-4 flex flex-wrap gap-2">
                {[1, 3, 5].map((quality) => (
                  <LoadingButton key={quality} className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100" onClick={() => review(activeReviewCard.id, quality)} loading={reviewingCardId === activeReviewCard.id} loadingText="送出中">
                    {quality === 1 ? "忘記" : quality === 3 ? "普通" : "熟悉"}
                  </LoadingButton>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-lg font-semibold">今日複習完成</div>
              <div className="mt-2 text-sm text-zinc-600">已複習 {reviewed} 張，熟悉 {remembered} 張。</div>
            </div>
          )}
        </section>
      )}
      <div className="mb-6 grid gap-4 lg:grid-cols-[360px_1fr]">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">生成與新增</h2>
          <label className="mb-1 block text-xs font-medium text-zinc-500" htmlFor="flashcard-doc">文件</label>
          <select id="flashcard-doc" className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={docId} onChange={(event) => setDocId(event.target.value)}>
            <option value="">不綁定文件</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}{doc.user_id !== user?.id ? "（課程共享）" : ""}
              </option>
            ))}
          </select>
          <LoadingButton
            className="mb-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            onClick={generate}
            disabled={!docId || streaming || user?.quota_status === "exceeded"}
            loading={streaming}
            loadingText="生成中"
            icon={<Wand2 size={16} />}
          >
            從文件生成 10 張
          </LoadingButton>
          <form className="space-y-3" onSubmit={createManual}>
            <label className="block text-xs font-medium text-zinc-500" htmlFor="flashcard-front">正面</label>
            <input id="flashcard-front" className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={front} onChange={(event) => setFront(event.target.value)} />
            <label className="block text-xs font-medium text-zinc-500" htmlFor="flashcard-back">背面</label>
            <textarea id="flashcard-back" className="min-h-24 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={back} onChange={(event) => setBack(event.target.value)} />
            <LoadingButton className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100" loading={creating} loadingText="新增中" icon={<Plus size={16} />}>
              新增閃卡
            </LoadingButton>
          </form>
        </section>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <AIGeneratedBadge />
          {preview && <pre aria-live="polite" className="max-h-64 overflow-auto rounded-md bg-zinc-50 p-3 text-xs text-zinc-700">{preview}</pre>}
          {error && <div role="alert" className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
          <div className="grid gap-3 sm:grid-cols-2">
            {cards.map((card) => (
              <article key={card.id} className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
                    <BrainCircuit size={16} className="shrink-0 text-zinc-500" />
                    <span className="break-words">{card.front}</span>
                  </div>
                  <button
                    className="shrink-0 rounded-md p-1.5 text-zinc-500 hover:bg-red-50 hover:text-red-600"
                    onClick={() => deleteCard(card)}
                    disabled={deletingCardId === card.id}
                    title="刪除閃卡"
                    aria-label="刪除閃卡"
                  >
                    {deletingCardId === card.id ? <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-red-200 border-t-red-600" /> : <Trash2 size={16} />}
                  </button>
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-700">{card.back}</div>
                <AIGeneratedBadge variant="inline" text="AI 或使用者建立內容，請自行驗證" />
                <div className="mt-3 flex flex-wrap gap-2">
                  {[1, 3, 5].map((quality) => (
                    <LoadingButton key={quality} className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100" onClick={() => review(card.id, quality)} loading={reviewingCardId === card.id} loadingText="送出中">
                      {quality === 1 ? "忘記" : quality === 3 ? "普通" : "熟悉"}
                    </LoadingButton>
                  ))}
                </div>
                <div className="mt-2 text-xs text-zinc-500">下次：{card.next_review.slice(0, 10)}</div>
              </article>
            ))}
            {cards.length === 0 && <div className="text-sm text-zinc-500">尚無閃卡</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
