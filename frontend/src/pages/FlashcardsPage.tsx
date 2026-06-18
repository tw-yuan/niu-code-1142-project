import { FormEvent, useEffect, useMemo, useState } from "react";
import { BrainCircuit, Plus, Trash2, Wand2 } from "lucide-react";
import { useLocation } from "react-router-dom";
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge";
import { LoadingButton } from "../components/app/LoadingButton";
import {
  apiFetch,
  DocumentItem,
  FlashcardItem,
  GenerationTask,
} from "../lib/api";
import { useGenerationTask } from "../lib/generation";
import { useAuthStore } from "../store/auth";

export function FlashcardsPage() {
  const user = useAuthStore((state) => state.user);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [cards, setCards] = useState<FlashcardItem[]>([]);
  const [docId, setDocId] = useState("");
  const [docIds, setDocIds] = useState<string[]>([]);
  const [courseId, setCourseId] = useState("");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [creating, setCreating] = useState(false);
  const [reviewingCardId, setReviewingCardId] = useState<string | null>(null);
  const [deletingCardId, setDeletingCardId] = useState<string | null>(null);
  const [reviewMode, setReviewMode] = useState(false);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [reviewed, setReviewed] = useState(0);
  const [remembered, setRemembered] = useState(0);
  const location = useLocation();

  const dueCards = useMemo(() => {
    const now = new Date().toISOString();
    return cards.filter((card) => card.next_review <= now);
  }, [cards]);
  const activeDocIds = docIds.length > 0 ? docIds : docId ? [docId] : [];
  const documentIds = documents.map((doc) => doc.id);
  const flashcardGeneration = useGenerationTask<{ count?: number }>(
    "flashcards",
    async () => {
      setPreview("");
      await load();
    },
  );

  async function load() {
    const [docs, nextCards] = await Promise.all([
      apiFetch<DocumentItem[]>("/documents"),
      apiFetch<FlashcardItem[]>("/flashcards"),
    ]);
    const ready = docs.filter((doc) => doc.status === "ready");
    setDocuments(ready);
    setCards(nextCards);
    if (!docId && docIds.length === 0 && ready[0]) {
      setDocId(ready[0].id);
      setDocIds([ready[0].id]);
    }
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const doc = params.get("doc");
    const docs = params.get("docs");
    const course = params.get("course");
    if (docs) {
      const nextDocIds = docs
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      setDocIds(nextDocIds);
      setDocId(nextDocIds[0] ?? "");
    } else if (doc) {
      setDocId(doc);
      setDocIds([doc]);
    }
    if (course) setCourseId(course);
    if (params.get("review") === "1") setReviewMode(true);
  }, [location.search]);

  async function generate() {
    if (activeDocIds.length === 0 || user?.quota_status === "exceeded") return;
    setStreaming(true);
    setError("");
    setPreview("");
    try {
      const task = await apiFetch<
        GenerationTask<{ count?: number }> | { task_id: string; status: string }
      >("/flashcards/jobs", {
        method: "POST",
        body: JSON.stringify({
          doc_id: activeDocIds[0],
          doc_ids: activeDocIds,
          course_id: courseId || undefined,
          count: 10,
        }),
      });
      flashcardGeneration.watch(task);
    } catch (err) {
      setError(err instanceof Error ? err.message : "閃卡生成失敗");
    } finally {
      setStreaming(false);
    }
  }

  async function createManual(event: FormEvent) {
    event.preventDefault();
    if (!front.trim() || !back.trim()) return;
    setCreating(true);
    try {
      await apiFetch("/flashcards", {
        method: "POST",
        body: JSON.stringify({
          front,
          back,
          doc_id: docId || activeDocIds[0] || null,
        }),
      });
      setFront("");
      setBack("");
      await load();
    } finally {
      setCreating(false);
    }
  }

  async function review(cardId: string, quality: number) {
    setReviewingCardId(cardId);
    try {
      await apiFetch(`/flashcards/${cardId}/review`, {
        method: "POST",
        body: JSON.stringify({ quality }),
      });
      setReviewed((prev) => prev + 1);
      if (quality >= 3) setRemembered((prev) => prev + 1);
      setReviewIndex((prev) => prev + 1);
      await load();
    } finally {
      setReviewingCardId(null);
    }
  }

  async function deleteCard(card: FlashcardItem) {
    setDeletingCardId(card.id);
    try {
      await apiFetch(`/flashcards/${card.id}`, { method: "DELETE" });
      await load();
    } finally {
      setDeletingCardId(null);
    }
  }

  const activeReviewCard = dueCards[reviewIndex];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">閃卡</h1>
        <p className="mt-1 text-sm text-zinc-500">
          待複習 {dueCards.length} 張
        </p>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <button
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-zinc-300"
          onClick={() => {
            setReviewMode(true);
            setReviewIndex(0);
            setReviewed(0);
            setRemembered(0);
          }}
          disabled={dueCards.length === 0}
        >
          開始今日複習
        </button>
        {reviewMode && (
          <button
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50"
            onClick={() => setReviewMode(false)}
          >
            回到列表
          </button>
        )}
      </div>
      {reviewMode && (
        <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          {activeReviewCard ? (
            <div>
              <div className="mb-2 text-xs text-zinc-500">
                第 {reviewIndex + 1} / {dueCards.length} 張
              </div>
              <div className="text-lg font-semibold">
                {activeReviewCard.front}
              </div>
              <div className="mt-4 whitespace-pre-wrap rounded-lg bg-zinc-50 p-4 text-sm leading-6 text-zinc-700">
                {activeReviewCard.back}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {[1, 3, 5].map((quality) => (
                  <LoadingButton
                    key={quality}
                    className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
                    onClick={() => review(activeReviewCard.id, quality)}
                    loading={reviewingCardId === activeReviewCard.id}
                    loadingText="送出中"
                  >
                    {quality === 1 ? "忘記" : quality === 3 ? "普通" : "熟悉"}
                  </LoadingButton>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-lg font-semibold">今日複習完成</div>
              <div className="mt-2 text-sm text-zinc-600">
                已複習 {reviewed} 張，熟悉 {remembered} 張。
              </div>
            </div>
          )}
        </section>
      )}
      <div className="mb-6 grid gap-4 lg:grid-cols-[360px_1fr]">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">生成與新增</h2>
          <div className="mb-1 text-xs font-medium text-zinc-500">文件</div>
          <div className="mb-3 max-h-44 overflow-auto rounded-lg border border-zinc-200 p-2">
            {documents.length > 0 && (
              <div className="mb-2 flex flex-wrap items-center gap-2 px-2">
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                  onClick={() => {
                    setDocIds(documentIds);
                    setDocId(documentIds[0] ?? "");
                  }}
                >
                  全選文件
                </button>
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                  onClick={() => {
                    setDocIds([]);
                    setDocId("");
                  }}
                >
                  清空
                </button>
                <span className="text-xs text-zinc-500">
                  已選 {docIds.length} / {documents.length}
                </span>
              </div>
            )}
            {documents.map((doc) => (
              <label
                key={doc.id}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-zinc-50"
              >
                <input
                  type="checkbox"
                  checked={docIds.includes(doc.id)}
                  onChange={(event) => {
                    setDocIds((current) => {
                      const next = event.target.checked
                        ? [...current, doc.id]
                        : current.filter((item) => item !== doc.id);
                      setDocId(next[0] ?? "");
                      return next;
                    });
                  }}
                />
                <span className="min-w-0 flex-1 truncate">
                  {doc.filename}
                  {doc.user_id !== user?.id ? "（課程共享）" : ""}
                </span>
              </label>
            ))}
            {documents.length === 0 && (
              <div className="px-2 py-3 text-sm text-zinc-500">
                尚無 ready 文件
              </div>
            )}
          </div>
          <LoadingButton
            className="mb-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            onClick={generate}
            disabled={
              activeDocIds.length === 0 ||
              streaming ||
              flashcardGeneration.active ||
              user?.quota_status === "exceeded"
            }
            loading={streaming || flashcardGeneration.active}
            loadingText="生成中"
            icon={<Wand2 size={16} />}
          >
            {activeDocIds.length > 1
              ? `從 ${activeDocIds.length} 個文件生成 10 張`
              : "從文件生成 10 張"}
          </LoadingButton>
          <form className="space-y-3" onSubmit={createManual}>
            <label
              className="block text-xs font-medium text-zinc-500"
              htmlFor="flashcard-front"
            >
              正面
            </label>
            <input
              id="flashcard-front"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={front}
              onChange={(event) => setFront(event.target.value)}
            />
            <label
              className="block text-xs font-medium text-zinc-500"
              htmlFor="flashcard-back"
            >
              背面
            </label>
            <textarea
              id="flashcard-back"
              className="min-h-24 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={back}
              onChange={(event) => setBack(event.target.value)}
            />
            <LoadingButton
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
              loading={creating}
              loadingText="新增中"
              icon={<Plus size={16} />}
            >
              新增閃卡
            </LoadingButton>
          </form>
        </section>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <AIGeneratedBadge />
          {preview && (
            <pre
              aria-live="polite"
              className="max-h-64 overflow-auto rounded-md bg-zinc-50 p-3 text-xs text-zinc-700"
            >
              {preview}
            </pre>
          )}
          {flashcardGeneration.active && (
            <div className="mb-4 rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-700">
              閃卡生成任務執行中，可先離開頁面，完成後回來會顯示在列表。
            </div>
          )}
          {flashcardGeneration.error && (
            <div
              role="alert"
              className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600"
            >
              {flashcardGeneration.error}
            </div>
          )}
          {error && (
            <div
              role="alert"
              className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600"
            >
              {error}
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {cards.map((card) => (
              <article
                key={card.id}
                className="rounded-lg border border-zinc-200 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
                    <BrainCircuit
                      size={16}
                      className="shrink-0 text-zinc-500"
                    />
                    <span className="break-words">{card.front}</span>
                  </div>
                  <button
                    className="shrink-0 rounded-md p-1.5 text-zinc-500 hover:bg-red-50 hover:text-red-600"
                    onClick={() => deleteCard(card)}
                    disabled={deletingCardId === card.id}
                    title="刪除閃卡"
                    aria-label="刪除閃卡"
                  >
                    {deletingCardId === card.id ? (
                      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-red-200 border-t-red-600" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-700">
                  {card.back}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {[1, 3, 5].map((quality) => (
                    <LoadingButton
                      key={quality}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
                      onClick={() => review(card.id, quality)}
                      loading={reviewingCardId === card.id}
                      loadingText="送出中"
                    >
                      {quality === 1 ? "忘記" : quality === 3 ? "普通" : "熟悉"}
                    </LoadingButton>
                  ))}
                </div>
                <div className="mt-2 text-xs text-zinc-500">
                  下次：{card.next_review.slice(0, 10)}
                </div>
              </article>
            ))}
            {cards.length === 0 && (
              <div className="text-sm text-zinc-500">尚無閃卡</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
