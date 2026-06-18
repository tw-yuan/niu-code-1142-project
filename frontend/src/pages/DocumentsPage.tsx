import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpenCheck,
  BrainCircuit,
  Eye,
  FileText,
  ListChecks,
  MessageSquareText,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  BASE_URL,
  apiFetch,
  apiUploadWithProgress,
  DocumentContent,
  DocumentItem,
  refreshToken,
} from "../lib/api";
import { LoadingButton } from "../components/app/LoadingButton";
import { MarkdownContent } from "../components/app/MarkdownContent";
import { useAuthStore } from "../store/auth";
import { wsManager } from "../lib/ws";

const MAX_UPLOAD_FILES = 10;

type UploadQueueItem = {
  id: string;
  filename: string;
  size: number;
  progress: number;
  status: "queued" | "uploading" | "processing" | "done" | "error";
  error?: string;
};

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentItem | null>(null);
  const [coverage, setCoverage] = useState<{ chapters: CoverageChapter[] }>({
    chapters: [],
  });
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [consentLoading, setConsentLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [archivingId, setArchivingId] = useState<string | null>(null);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [consented, setConsented] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { id } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const selectedDocs = useMemo(
    () => documents.filter((doc) => selectedDocIds.includes(doc.id)),
    [documents, selectedDocIds],
  );
  const ownedDocuments = useMemo(
    () => documents.filter((doc) => doc.user_id === user?.id),
    [documents, user?.id],
  );
  const sharedDocuments = useMemo(
    () => documents.filter((doc) => doc.user_id !== user?.id),
    [documents, user?.id],
  );
  const selectedReadyDocs = selectedDocs.filter(
    (doc) => doc.status === "ready",
  );
  const selectedOwnedDocs = selectedDocs.filter(
    (doc) => doc.user_id === user?.id,
  );
  const allOwnedSelected =
    ownedDocuments.length > 0 &&
    ownedDocuments.every((doc) => selectedDocIds.includes(doc.id));
  const allSharedSelected =
    sharedDocuments.length > 0 &&
    sharedDocuments.every((doc) => selectedDocIds.includes(doc.id));

  async function loadDocuments(showSpinner = false) {
    if (showSpinner) setRefreshing(true);
    try {
      const data = await apiFetch<DocumentItem[]>("/documents");
      setDocuments(data);
      const active = id ? data.find((doc) => doc.id === id) : null;
      setSelected(active ?? data[0] ?? null);
    } finally {
      if (showSpinner) setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDocuments().catch(() => undefined);
    apiFetch<Array<{ consent_type: string }>>("/legal/consents")
      .then((items) =>
        setConsented(
          items.some((item) => item.consent_type === "copyright_declaration"),
        ),
      )
      .catch(() => undefined);
    const token = localStorage.getItem("access_token");
    if (token) wsManager.connect(token);
    const offStatus = wsManager.on("doc_status", () =>
      loadDocuments().catch(() => undefined),
    );
    const offReady = wsManager.on("doc_ready", () =>
      loadDocuments().catch(() => undefined),
    );
    return () => {
      offStatus();
      offReady();
    };
  }, [id]);

  useEffect(() => {
    if (!selected) return;
    apiFetch<{ chapters: CoverageChapter[] }>(
      `/documents/${selected.id}/coverage`,
    )
      .then(setCoverage)
      .catch(() => setCoverage({ chapters: [] }));
    setContent(null);
  }, [selected]);

  useEffect(() => {
    if (!selected?.page_count) {
      setPreviewUrl("");
      return;
    }
    let objectUrl = "";
    let active = true;
    loadAuthorizedBlob(`/documents/${selected.id}/pages/1`)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      })
      .catch(() => setPreviewUrl(""));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selected?.id, selected?.page_count]);

  useEffect(() => {
    setSelectedDocIds((current) =>
      current.filter((docId) => documents.some((doc) => doc.id === docId)),
    );
  }, [documents]);

  async function uploadFiles(files: File[]) {
    if (files.length === 0) return;
    setLoading(true);
    setError("");
    const queueItems = files.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      filename: file.name,
      size: file.size,
      progress: 0,
      status: "queued" as const,
    }));
    setUploadQueue((current) => [...queueItems, ...current]);
    const failures: string[] = [];
    try {
      await Promise.all(
        files.map(async (file, index) => {
          const itemId = queueItems[index].id;
          setUploadQueueItem(itemId, { status: "uploading", progress: 1 });
          try {
            await apiUploadWithProgress<DocumentItem>(
              "/documents/upload",
              file,
              (progress) => setUploadQueueItem(itemId, { progress }),
            );
            setUploadQueueItem(itemId, {
              status: "processing",
              progress: 100,
            });
          } catch (err) {
            const message = err instanceof Error ? err.message : "上傳失敗";
            failures.push(`${file.name}: ${message}`);
            setUploadQueueItem(itemId, {
              status: "error",
              error: message,
              progress: 100,
            });
          }
        }),
      );
      if (failures.length > 0) {
        setError(failures.join("；"));
      }
      await loadDocuments();
      setUploadQueue((current) =>
        current.map((item) =>
          queueItems.some((queued) => queued.id === item.id) &&
          item.status === "processing"
            ? { ...item, status: "done" }
            : item,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "上傳失敗");
    } finally {
      setLoading(false);
      setPendingFiles([]);
    }
  }

  function setUploadQueueItem(id: string, patch: Partial<UploadQueueItem>) {
    setUploadQueue((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) return;
    if (files.length > MAX_UPLOAD_FILES) {
      setError(`一次最多上傳 ${MAX_UPLOAD_FILES} 個檔案，請分批上傳。`);
      event.target.value = "";
      return;
    }
    if (!consented) {
      setPendingFiles(files);
    } else {
      uploadFiles(files).catch(() => undefined);
    }
    event.target.value = "";
  }

  async function acceptConsentAndUpload() {
    setConsentLoading(true);
    try {
      await apiFetch("/legal/consent", {
        method: "POST",
        body: JSON.stringify({ consent_type: "copyright_declaration" }),
      });
      setConsented(true);
      if (pendingFiles.length > 0) await uploadFiles(pendingFiles);
    } finally {
      setConsentLoading(false);
    }
  }

  async function deleteDocument(docId: string) {
    setDeletingId(docId);
    try {
      await apiFetch(`/documents/${docId}`, { method: "DELETE" });
      if (selected?.id === docId) {
        setSelected(null);
        navigate("/documents");
      }
      await loadDocuments();
    } finally {
      setDeletingId(null);
    }
  }

  async function archiveDocument(docId: string) {
    setArchivingId(docId);
    try {
      await apiFetch(`/documents/${docId}/archive`, { method: "POST" });
      await loadDocuments();
    } finally {
      setArchivingId(null);
    }
  }

  async function restoreDocument(docId: string) {
    setArchivingId(docId);
    try {
      await apiFetch(`/documents/${docId}/restore`, { method: "POST" });
      await loadDocuments();
    } finally {
      setArchivingId(null);
    }
  }

  async function deleteSelectedDocuments() {
    if (selectedOwnedDocs.length === 0) return;
    setBatchDeleting(true);
    try {
      for (const doc of selectedOwnedDocs) {
        await apiFetch(`/documents/${doc.id}`, { method: "DELETE" });
      }
      if (selected && selectedOwnedDocs.some((doc) => doc.id === selected.id)) {
        setSelected(null);
        navigate("/documents");
      }
      setSelectedDocIds((current) =>
        current.filter(
          (docId) => !selectedOwnedDocs.some((doc) => doc.id === docId),
        ),
      );
      await loadDocuments();
    } finally {
      setBatchDeleting(false);
    }
  }

  function toggleDocSelection(docId: string) {
    setSelectedDocIds((current) =>
      current.includes(docId)
        ? current.filter((item) => item !== docId)
        : [...current, docId],
    );
  }

  function toggleDocumentGroup(
    groupDocs: DocumentItem[],
    shouldSelect: boolean,
  ) {
    setSelectedDocIds((current) => {
      const next = new Set(current);
      groupDocs.forEach((doc) => {
        if (shouldSelect) {
          next.add(doc.id);
        } else {
          next.delete(doc.id);
        }
      });
      return Array.from(next);
    });
  }

  function openBatchChat() {
    if (selectedReadyDocs.length === 0) return;
    navigate(
      `/chat?docs=${selectedReadyDocs.map((doc) => encodeURIComponent(doc.id)).join(",")}`,
    );
  }

  function openBatchQuiz() {
    if (selectedReadyDocs.length === 0) return;
    navigate(
      `/quiz/generate?docs=${selectedReadyDocs.map((doc) => encodeURIComponent(doc.id)).join(",")}`,
    );
  }

  function openBatchFlashcards() {
    if (selectedReadyDocs.length === 0) return;
    navigate(
      `/flashcards?docs=${selectedReadyDocs.map((doc) => encodeURIComponent(doc.id)).join(",")}`,
    );
  }

  async function loadContent() {
    if (!selected) return;
    setContentLoading(true);
    try {
      setContent(
        await apiFetch<DocumentContent>(`/documents/${selected.id}/content`),
      );
    } finally {
      setContentLoading(false);
    }
  }

  function renderDocumentSection(
    title: string,
    docs: DocumentItem[],
    allGroupSelected: boolean,
    onToggleAll: () => void,
    emptyText: string,
  ) {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
            <p className="mt-1 text-xs text-zinc-500">{docs.length} 個文件</p>
          </div>
        </div>
        <div className="grid grid-cols-[44px_1fr_120px_120px] border-b border-zinc-200 px-5 py-3 text-xs font-medium uppercase text-zinc-500">
          <label
            className="flex items-center"
            title={allGroupSelected ? "取消全選" : "全選文件"}
          >
            <input
              className="h-4 w-4 rounded border-zinc-300 text-indigo-600"
              type="checkbox"
              checked={allGroupSelected}
              onChange={onToggleAll}
              disabled={docs.length === 0}
              aria-label={
                allGroupSelected ? `取消全選${title}` : `全選${title}`
              }
            />
          </label>
          <div>名稱</div>
          <div>狀態</div>
          <div className="text-right">大小</div>
        </div>
        <div className="divide-y divide-zinc-100">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className={[
                "grid grid-cols-[44px_1fr_120px_120px] items-center px-5 py-4 text-sm hover:bg-zinc-50",
                selectedDocIds.includes(doc.id) ? "bg-indigo-50/60" : "",
              ].join(" ")}
            >
              <label className="flex items-center" title="選取文件">
                <input
                  className="h-4 w-4 rounded border-zinc-300 text-indigo-600"
                  type="checkbox"
                  checked={selectedDocIds.includes(doc.id)}
                  onChange={() => toggleDocSelection(doc.id)}
                  aria-label={`選取 ${doc.filename}`}
                />
              </label>
              <button
                className="flex min-w-0 items-center gap-3 text-left"
                onClick={() => {
                  setSelected(doc);
                  navigate(`/documents/${doc.id}`);
                }}
              >
                <FileText size={18} className="shrink-0 text-zinc-500" />
                <div className="min-w-0">
                  <div className="truncate font-medium">{doc.filename}</div>
                  <div className="text-xs text-zinc-500">
                    {doc.page_count ?? 0} 頁 · {doc.chunk_count ?? 0} chunks
                    {doc.user_id !== user?.id ? " · 課程共享" : ""}
                    {doc.course_status === "removed" ? " · 已移出課程" : ""}
                  </div>
                </div>
              </button>
              <span className={statusClass(doc.status)}>
                {statusLabel(doc.status)}
              </span>
              <div className="text-right text-zinc-500">
                {formatBytes(doc.file_size)}
              </div>
            </div>
          ))}
          {docs.length === 0 && (
            <div className="px-5 py-12 text-center text-sm text-zinc-500">
              {loading ? "上傳中" : emptyText}
            </div>
          )}
        </div>
      </section>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">文件</h1>
          <p className="mt-1 text-sm text-zinc-500">
            PDF、Markdown、PPTX、DOCX
          </p>
        </div>
        <div className="flex items-center gap-2">
          <LoadingButton
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
            onClick={() => loadDocuments(true)}
            loading={refreshing}
            loadingText="更新中"
            icon={<RefreshCw size={16} />}
          >
            重新整理
          </LoadingButton>
          <label
            className={[
              "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white",
              loading
                ? "cursor-not-allowed bg-zinc-300"
                : "cursor-pointer bg-indigo-600 hover:bg-indigo-700",
            ].join(" ")}
          >
            {loading ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/50 border-t-white" />
            ) : (
              <Upload size={16} />
            )}
            {loading ? "上傳中" : "上傳"}
            <input
              className="hidden"
              type="file"
              accept=".pdf,.md,.pptx,.docx"
              multiple
              onChange={onFile}
              disabled={loading}
            />
          </label>
        </div>
      </div>
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}
      {uploadQueue.length > 0 && (
        <section className="mb-4 rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-zinc-200 px-5 py-3">
            <div>
              <h2 className="text-sm font-semibold text-zinc-900">上傳佇列</h2>
              <p className="mt-1 text-xs text-zinc-500">
                {uploadQueue.length} 個檔案
              </p>
            </div>
            {uploadQueue.some((item) =>
              ["done", "error"].includes(item.status),
            ) && (
              <button
                className="rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-50"
                onClick={() =>
                  setUploadQueue((current) =>
                    current.filter(
                      (item) => !["done", "error"].includes(item.status),
                    ),
                  )
                }
              >
                清除完成
              </button>
            )}
          </div>
          <div className="divide-y divide-zinc-100">
            {uploadQueue.map((item) => (
              <div
                key={item.id}
                className="grid gap-3 px-5 py-3 text-sm md:grid-cols-[minmax(0,1fr)_120px_160px]"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium text-zinc-900">
                    {item.filename}
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">
                    {formatBytes(item.size)}
                    {item.error ? ` · ${item.error}` : ""}
                  </div>
                </div>
                <span className={uploadStatusClass(item.status)}>
                  {uploadStatusLabel(item.status)}
                </span>
                <div>
                  <div className="mb-1 text-right text-xs text-zinc-500">
                    {item.progress}%
                  </div>
                  <div className="h-2 rounded-full bg-zinc-100">
                    <div
                      className={[
                        "h-2 rounded-full transition-all",
                        item.status === "error"
                          ? "bg-red-500"
                          : "bg-indigo-600",
                      ].join(" ")}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          {selectedDocIds.length > 0 && (
            <section className="flex flex-col gap-3 rounded-lg border border-indigo-100 bg-indigo-50 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-indigo-800">
                已選擇 {selectedDocIds.length} 個文件
                {selectedReadyDocs.length !== selectedDocIds.length && (
                  <span className="ml-2 text-xs text-indigo-600">
                    只有 ready 文件可用於對話/測驗/閃卡
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                  onClick={openBatchChat}
                  disabled={selectedReadyDocs.length === 0}
                >
                  <MessageSquareText size={16} />
                  多檔對話
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm text-indigo-700 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                  onClick={openBatchQuiz}
                  disabled={selectedReadyDocs.length === 0}
                >
                  <ListChecks size={16} />
                  多檔測驗
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm text-indigo-700 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                  onClick={openBatchFlashcards}
                  disabled={selectedReadyDocs.length === 0}
                >
                  <BrainCircuit size={16} />
                  多檔閃卡
                </button>
                <LoadingButton
                  className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                  onClick={deleteSelectedDocuments}
                  disabled={selectedOwnedDocs.length === 0}
                  loading={batchDeleting}
                  loadingText="刪除中"
                  icon={<Trash2 size={16} />}
                >
                  刪除可刪除 {selectedOwnedDocs.length}
                </LoadingButton>
                <button
                  className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-50"
                  onClick={() => setSelectedDocIds([])}
                >
                  清除選取
                </button>
              </div>
            </section>
          )}
          {renderDocumentSection(
            "我的文件",
            ownedDocuments,
            allOwnedSelected,
            () => toggleDocumentGroup(ownedDocuments, !allOwnedSelected),
            "尚無自己的文件",
          )}
          {renderDocumentSection(
            "課程共享文件",
            sharedDocuments,
            allSharedSelected,
            () => toggleDocumentGroup(sharedDocuments, !allSharedSelected),
            "尚無課程共享文件",
          )}
        </div>
        <aside className="rounded-lg border border-zinc-200 bg-white shadow-sm">
          {selected ? (
            <div>
              <div className="border-b border-zinc-200 p-5">
                <div className="text-sm font-semibold">{selected.filename}</div>
                <div className="mt-1 text-xs text-zinc-500">
                  {selected.page_count ?? 0} 頁 · {selected.chunk_count ?? 0}{" "}
                  chunks
                </div>
                {selected.user_id !== user?.id && (
                  <div className="mt-2 inline-flex rounded-md bg-indigo-50 px-2 py-1 text-xs text-indigo-700">
                    {selected.course_status === "removed"
                      ? "已移出課程"
                      : "課程共享文件"}
                  </div>
                )}
              </div>
              <div className="space-y-3 p-5">
                {selected.status === "ready" && (
                  <div className="flex flex-wrap gap-2">
                    <Link
                      className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                      to={`/chat?doc=${selected.id}`}
                    >
                      <MessageSquareText size={16} />
                      開始對話
                    </Link>
                    <Link
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                      to={`/summary/${selected.id}`}
                    >
                      <BookOpenCheck size={16} />
                      摘要
                    </Link>
                    <Link
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                      to={`/mindmap/${selected.id}`}
                    >
                      心智圖
                    </Link>
                    <Link
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                      to={`/quiz/generate?doc=${selected.id}`}
                    >
                      生成測驗
                    </Link>
                    <Link
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                      to={`/flashcards?doc=${selected.id}`}
                    >
                      建立閃卡
                    </Link>
                    <LoadingButton
                      className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
                      onClick={loadContent}
                      loading={contentLoading}
                      loadingText="載入中"
                      icon={<Eye size={16} />}
                    >
                      瀏覽內容
                    </LoadingButton>
                  </div>
                )}
                {selected.status === "error" && selected.error_msg && (
                  <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                    {selected.error_msg}
                  </div>
                )}
                {previewUrl ? (
                  <img
                    className="aspect-[3/4] w-full rounded-md border border-zinc-200 object-contain"
                    src={previewUrl}
                    alt="文件第一頁預覽"
                  />
                ) : (
                  <div className="rounded-md border border-dashed border-zinc-200 p-6 text-center text-sm text-zinc-500">
                    尚無頁面預覽
                  </div>
                )}
                <div>
                  <div className="mb-2 text-sm font-medium">學習覆蓋度</div>
                  <div className="space-y-2">
                    {coverage.chapters.map((chapter) => (
                      <div key={chapter.title}>
                        <div className="mb-1 flex justify-between text-xs text-zinc-500">
                          <span>{chapter.title}</span>
                          <span>
                            {Math.round(chapter.coverage_score * 100)}%
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-zinc-100">
                          <div
                            className="h-2 rounded-full bg-indigo-600"
                            style={{
                              width: `${Math.round(chapter.coverage_score * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                    {coverage.chapters.length === 0 && (
                      <div className="text-sm text-zinc-500">尚無學習記錄</div>
                    )}
                  </div>
                </div>
                {contentLoading && (
                  <div className="rounded-md bg-zinc-50 p-3 text-sm text-zinc-500">
                    載入文件內容中
                  </div>
                )}
                {content && (
                  <div className="max-h-96 overflow-auto rounded-lg border border-zinc-200 p-4">
                    <MarkdownContent className="text-sm">
                      {content.content || "尚無可瀏覽文字"}
                    </MarkdownContent>
                  </div>
                )}
                {selected.user_id === user?.id && (
                  <div className="flex flex-wrap gap-2">
                    {selected.status === "archived" ? (
                      <LoadingButton
                        className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                        onClick={() => restoreDocument(selected.id)}
                        loading={archivingId === selected.id}
                        loadingText="還原中"
                        icon={<RefreshCw size={16} />}
                      >
                        還原文件
                      </LoadingButton>
                    ) : (
                      <LoadingButton
                        className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                        onClick={() => archiveDocument(selected.id)}
                        loading={archivingId === selected.id}
                        loadingText="封存中"
                        icon={<RefreshCw size={16} />}
                        disabled={selected.status !== "ready"}
                      >
                        封存文件
                      </LoadingButton>
                    )}
                    <LoadingButton
                      className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                      onClick={() => deleteDocument(selected.id)}
                      loading={deletingId === selected.id}
                      loadingText="刪除中"
                      icon={<Trash2 size={16} />}
                    >
                      刪除文件
                    </LoadingButton>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-6 text-sm text-zinc-500">選擇文件查看詳情</div>
          )}
        </aside>
      </div>
      {pendingFiles.length > 0 && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-zinc-950/30 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-lg font-semibold">上傳前著作權聲明</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-600">
              您選擇的 {pendingFiles.length}{" "}
              個文件必須為您合法持有的資料，或已獲得著作權人授權。本平台一次最多上傳{" "}
              {MAX_UPLOAD_FILES}{" "}
              個檔案，且僅供個人學習使用，違反著作權法的責任由上傳者自行承擔。
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                onClick={() => setPendingFiles([])}
                disabled={consentLoading}
              >
                取消
              </button>
              <LoadingButton
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
                onClick={acceptConsentAndUpload}
                loading={consentLoading || loading}
                loadingText="送出中"
              >
                我已了解並同意
              </LoadingButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface CoverageChapter {
  title: string;
  page_range: [number, number];
  quiz_attempts: number;
  quiz_score_avg: number;
  flashcard_count: number;
  flashcard_mastered: number;
  chat_mentions: number;
  coverage_score: number;
}

function statusClass(status: string) {
  const base = "inline-flex w-fit rounded-lg px-2 py-1 text-xs";
  if (status === "ready") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "archived") return `${base} bg-zinc-100 text-zinc-600`;
  if (status === "error") return `${base} bg-red-50 text-red-600`;
  return `${base} bg-indigo-50 text-indigo-700`;
}

function statusLabel(status: string) {
  if (status === "ready") return "可用";
  if (status === "archived") return "封存";
  if (status === "error") return "錯誤";
  return status;
}

function uploadStatusLabel(status: UploadQueueItem["status"]) {
  if (status === "queued") return "排隊中";
  if (status === "uploading") return "上傳中";
  if (status === "processing") return "等待處理";
  if (status === "done") return "已送出";
  return "失敗";
}

function uploadStatusClass(status: UploadQueueItem["status"]) {
  const base = "inline-flex h-fit w-fit rounded-lg px-2 py-1 text-xs";
  if (status === "error") return `${base} bg-red-50 text-red-600`;
  if (status === "done") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "processing") return `${base} bg-amber-50 text-amber-700`;
  return `${base} bg-indigo-50 text-indigo-700`;
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function loadAuthorizedBlob(path: string): Promise<Blob> {
  let res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  if (res.status === 401 && (await refreshToken())) {
    res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  }
  if (!res.ok) throw new Error("Failed to load file");
  return res.blob();
}

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}
