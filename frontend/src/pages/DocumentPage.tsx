import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import DirectionCard from "../components/DirectionCard";
import { getDocument, getDirections, retryDocument } from "../api/documents";
import { createSession } from "../api/sessions";
import type { Document, Direction } from "../api/documents";

export default function DocumentPage() {
  const { docId } = useParams<{ docId: string }>();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<Document | null>(null);
  const [directions, setDirections] = useState<Direction[]>([]);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [loadingDirs, setLoadingDirs] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const directionsLoadedRef = useRef(false);

  const loadDirections = useCallback(async (refresh: boolean) => {
    if (!docId) return;
    if (refresh) setRefreshing(true);
    else setLoadingDirs(true);
    try {
      const result = await getDirections(Number(docId), refresh);
      setDirections(result.directions);
    } catch {
      setDirections([]);
    } finally {
      setLoadingDirs(false);
      setRefreshing(false);
    }
  }, [docId]);

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    let timer: number | undefined;

    async function loadDoc() {
      const nextDoc = await getDocument(Number(docId));
      if (cancelled) return;
      setDoc(nextDoc);
      setLoadingDoc(false);
      if (nextDoc.parse_status === "ready") {
        if (!directionsLoadedRef.current) {
          directionsLoadedRef.current = true;
          await loadDirections(false);
        }
        if (nextDoc.token_count >= 12000 && !["indexed", "failed"].includes(nextDoc.index_status)) {
          timer = window.setTimeout(loadDoc, 2000);
        }
      } else if (nextDoc.parse_status !== "failed") {
        timer = window.setTimeout(loadDoc, 2000);
      } else {
        setLoadingDirs(false);
      }
    }

    loadDoc().catch(() => {
      if (!cancelled) {
        setLoadingDoc(false);
        setLoadingDirs(false);
      }
    });

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [docId, loadDirections, reloadTick]);

  async function handleDirectionClick(dir: Direction) {
    if (!docId) return;
    setStarting(dir.key);
    try {
      const session = await createSession({
        document_id: Number(docId),
        direction_key: dir.key,
        direction_label: dir.label,
        direction_description: dir.description,
        direction_emoji: dir.emoji,
      });
      navigate(`/sessions/${session.id}`, {
        state: {
          documentId: Number(docId),
          autoStartPrompt: getDirectionStartPrompt(dir),
        },
      });
    } finally {
      setStarting(null);
    }
  }

  async function handleRetry() {
    if (!docId) return;
    const nextDoc = await retryDocument(Number(docId));
    setLoadingDoc(true);
    setLoadingDirs(true);
    setDoc(nextDoc);
    setDirections([]);
    directionsLoadedRef.current = false;
    setLoadingDirs(true);
    setReloadTick((v) => v + 1);
  }

  const fixedDirs = directions.filter((d) => !d.is_dynamic);
  const dynamicDirs = directions.filter((d) => d.is_dynamic);

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate("/")}
          className="text-sm text-gray-400 hover:text-indigo-500 mb-6 flex items-center gap-1"
        >
          ← 返回講義列表
        </button>

        {loadingDoc ? (
          <LoadingDocumentCard />
        ) : doc ? (
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-8">
            <div className="flex items-start gap-4">
              <div className="text-3xl">
                {doc.file_type === "pdf" ? "📕" : doc.file_type === "docx" ? "📘" : "📄"}
              </div>
              <div>
                <h2 className="font-semibold text-gray-800 text-lg">{doc.original_filename}</h2>
                <p className="text-sm text-gray-400 mt-0.5">
                  {doc.token_count.toLocaleString()} tokens
                  <StatusLabel doc={doc} />
                </p>
                {doc.error_message && (
                  <p className="text-xs text-red-500 mt-2 break-words">{doc.error_message}</p>
                )}
                {doc.parse_status === "failed" && (
                  <button
                    onClick={handleRetry}
                    className="text-xs text-indigo-600 hover:underline mt-2"
                  >
                    重新解析
                  </button>
                )}
              </div>
            </div>
            <DocumentProgress doc={doc} />
          </div>
        ) : (
          <p className="text-red-500">找不到此文件</p>
        )}

        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700">選擇學習方向</h3>
          <button
            onClick={() => loadDirections(true)}
            disabled={loadingDirs || refreshing || doc?.parse_status !== "ready"}
            className="text-xs text-gray-400 hover:text-indigo-500 disabled:opacity-40 flex items-center gap-1"
          >
            {refreshing ? "生成中..." : "↻ 重新生成推薦"}
          </button>
        </div>

        {doc?.parse_status !== "ready" ? (
          <div className="rounded-xl border border-dashed border-gray-200 bg-white p-6 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
              講義解析完成後會自動顯示學習方向。
            </div>
          </div>
        ) : loadingDirs ? (
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500">
            <div className="flex items-center gap-3">
              <span className="h-5 w-5 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin" />
              正在分析講義並生成學習方向...
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {fixedDirs.map((dir) => (
                <div key={dir.key} className={starting === dir.key ? "opacity-50 pointer-events-none" : ""}>
                  <DirectionCard direction={dir} onClick={() => handleDirectionClick(dir)} />
                </div>
              ))}
            </div>

            {dynamicDirs.length > 0 && (
              <>
                <h4 className="text-sm font-medium text-indigo-600 mb-3">✨ 專為這份講義推薦</h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {dynamicDirs.map((dir) => (
                    <div key={dir.key} className={starting === dir.key ? "opacity-50 pointer-events-none" : ""}>
                      <DirectionCard direction={dir} onClick={() => handleDirectionClick(dir)} />
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function getDirectionStartPrompt(dir: Direction) {
  const prompts: Record<string, string> = {
    summary: "請根據這份講義內容，生成完整的章節摘要，以條列重點的方式呈現。",
    quiz: "請根據這份講義內容出 5 道測驗題（混合選擇題與問答題），等我作答後再逐題批改。",
    explain: "請先介紹這份講義的主要主題與核心概念，讓我建立整體的理解。",
    qa: "請先根據這份講義整理可以深入提問的主題，並列出 3 個建議問題。",
  };
  return prompts[dir.key] ?? `我選擇了「${dir.label}」這個學習方向，請根據講義內容開始輔助我學習。`;
}

function LoadingDocumentCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 mb-8 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="h-10 w-10 rounded-lg bg-gray-100" />
        <div className="flex-1">
          <div className="h-5 w-2/3 rounded bg-gray-100" />
          <div className="mt-3 h-3 w-1/3 rounded bg-gray-100" />
          <div className="mt-5 h-2 rounded-full bg-gray-100" />
        </div>
      </div>
    </div>
  );
}

function DocumentProgress({ doc }: { doc: Document }) {
  const steps = [
    { key: "uploaded", label: "接收檔案" },
    { key: "parsing", label: "解析內容" },
    { key: "indexing", label: doc.token_count >= 12000 ? "建立索引" : "準備全文" },
    { key: "ready", label: "完成" },
  ];
  const progress = getProgress(doc);
  const active = getActiveStep(doc);
  const failed = doc.parse_status === "failed" || doc.index_status === "failed";

  return (
    <div className="mt-5 border-t border-gray-100 pt-5">
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className={failed ? "text-red-500" : "text-gray-400"}>{getProgressText(doc)}</span>
        <span className="font-medium text-gray-400">{progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            failed ? "bg-red-400" : "bg-indigo-500"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="mt-4 grid grid-cols-4 gap-2">
        {steps.map((step, index) => {
          const isDone = index < active && !failed;
          const isActive = index === active && !failed;
          return (
            <div key={step.key} className="flex items-center gap-2 text-xs text-gray-400">
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                  isDone
                    ? "border-emerald-400 bg-emerald-400 text-white"
                    : isActive
                      ? "border-indigo-400 bg-indigo-50 text-indigo-500 animate-pulse"
                      : failed && index === active
                        ? "border-red-400 bg-red-50 text-red-500"
                        : "border-gray-200 bg-white"
                }`}
              >
                {isDone ? "✓" : index + 1}
              </span>
              <span className={isActive ? "text-indigo-600 font-medium" : ""}>{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getProgress(doc: Document) {
  if (doc.parse_status === "failed" || doc.index_status === "failed") return 100;
  if (doc.parse_status === "uploaded") return 25;
  if (doc.parse_status === "parsing") return 50;
  if (doc.parse_status === "ready" && doc.token_count >= 12000 && doc.index_status !== "indexed") return 78;
  return 100;
}

function getActiveStep(doc: Document) {
  if (doc.parse_status === "uploaded") return 0;
  if (doc.parse_status === "parsing") return 1;
  if (doc.parse_status === "failed") return 1;
  if (doc.token_count >= 12000 && doc.index_status !== "indexed") return 2;
  if (doc.index_status === "failed") return 2;
  return 3;
}

function getProgressText(doc: Document) {
  if (doc.parse_status === "failed") return "解析失敗，請查看錯誤訊息後重試";
  if (doc.index_status === "failed") return "內容已解析，向量索引失敗，仍可用全文/備援模式學習";
  if (doc.parse_status === "uploaded") return "檔案已收到，等待背景工作開始解析";
  if (doc.parse_status === "parsing") return "正在解析講義內容，掃描 PDF 或圖片會花比較久";
  if (doc.token_count >= 12000 && doc.index_status !== "indexed") return "內容解析完成，正在建立長文件向量索引";
  return "講義已準備完成，可以選擇學習方向";
}

function StatusLabel({ doc }: { doc: Document }) {
  if (doc.parse_status === "failed") {
    return <span className="ml-2 text-red-500">解析失敗</span>;
  }
  if (doc.parse_status !== "ready") {
    return <span className="ml-2 text-amber-500">解析中</span>;
  }
  if (doc.token_count >= 12000) {
    if (doc.index_status === "indexed") {
      return <span className="ml-2 text-emerald-500">已建立向量索引</span>;
    }
    if (doc.index_status === "failed") {
      return <span className="ml-2 text-red-500">索引失敗</span>;
    }
    return <span className="ml-2 text-amber-500">索引中</span>;
  }
  return <span className="ml-2 text-blue-400">全文模式</span>;
}
