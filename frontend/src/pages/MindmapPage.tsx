import { KeyboardEvent, useCallback, useEffect, useState } from "react";
import { CheckCircle2, FileText, GitBranch, Wand2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge";
import { GenerationTaskStatus } from "../components/app/GenerationTaskPanel";
import { LoadingButton } from "../components/app/LoadingButton";
import { MarkdownContent } from "../components/app/MarkdownContent";
import { MindmapCanvas } from "../components/app/MindmapCanvas";
import {
  apiFetch,
  DocumentItem,
  GenerationTask,
  MindmapDocumentStatus,
  MindmapResponse,
  MindmapTree,
} from "../lib/api";
import { useGenerationTask } from "../lib/generation";
import { streamFetch } from "../lib/stream";
import { useAuthStore } from "../store/auth";

export function MindmapPage() {
  const { docId } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [documentStatuses, setDocumentStatuses] = useState<
    MindmapDocumentStatus[]
  >([]);
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [content, setContent] = useState("");
  const [tree, setTree] = useState<MindmapTree | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [format, setFormat] = useState<"tree_json" | "markdown" | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loadingList, setLoadingList] = useState(false);
  const activeDocId = docId ?? selectedDocId;
  const activeStatus = documentStatuses.find(
    (item) => item.document.id === activeDocId,
  );

  const loadDocumentStatuses = useCallback(async () => {
    setLoadingList(true);
    try {
      const items = await apiFetch<MindmapDocumentStatus[]>("/mindmap");
      setDocumentStatuses(items);
      if (docId && !items.some((item) => item.document.id === docId)) {
        navigate("/mindmap", { replace: true });
      } else if (!docId && !selectedDocId && items[0]) {
        setSelectedDocId(items[0].document.id);
      }
    } finally {
      setLoadingList(false);
    }
  }, [docId, navigate, selectedDocId]);

  const handleMindmapGenerated = useCallback(
    async (
      task: GenerationTask<{
        mindmap_id?: string;
        format?: "tree_json" | "markdown";
        schema_version?: number;
        tree?: MindmapTree;
        content?: string;
      }>,
    ) => {
      const output = task.output;
      if (output?.tree) {
        setTree(output.tree);
        setContent(output.content ?? treeToMarkdown(output.tree));
        setArtifactId(output.mindmap_id ?? task.artifact_id);
        setFormat(output.format ?? "tree_json");
        await loadDocumentStatuses();
        return;
      }
      const currentDocId = docId ?? selectedDocId;
      if (currentDocId) {
        const data = await apiFetch<MindmapResponse>(
          `/mindmap/${currentDocId}`,
        );
        setContent(data.content);
        setTree(data.tree);
        setArtifactId(data.id);
        setFormat(data.format);
        await loadDocumentStatuses();
      }
    },
    [docId, loadDocumentStatuses, selectedDocId],
  );

  const matchMindmapTask = useCallback(
    (
      task: GenerationTask<{
        mindmap_id?: string;
        format?: "tree_json" | "markdown";
        schema_version?: number;
        tree?: MindmapTree;
        content?: string;
      }>,
    ) => task.input.doc_id === activeDocId,
    [activeDocId],
  );
  const mindmapGeneration = useGenerationTask<{
    mindmap_id?: string;
    format?: "tree_json" | "markdown";
    schema_version?: number;
    tree?: MindmapTree;
    content?: string;
  }>("mindmap", handleMindmapGenerated, matchMindmapTask);

  useEffect(() => {
    loadDocumentStatuses().catch(() => setDocumentStatuses([]));
  }, [loadDocumentStatuses]);

  useEffect(() => {
    if (!activeDocId) {
      setDoc(null);
      setContent("");
      setTree(null);
      setArtifactId(null);
      setFormat(null);
      return;
    }
    const statusDoc = activeStatus?.document ?? null;
    if (statusDoc) setDoc(statusDoc);
    else
      apiFetch<DocumentItem>(`/documents/${activeDocId}`)
        .then(setDoc)
        .catch(() => undefined);
    setError("");
    apiFetch<MindmapResponse>(`/mindmap/${activeDocId}`)
      .then((data) => {
        setContent(data.content);
        setTree(data.tree);
        setArtifactId(data.id);
        setFormat(data.format);
      })
      .catch(() => {
        setContent("");
        setTree(null);
        setArtifactId(null);
        setFormat(null);
      });
  }, [activeDocId, activeStatus?.document]);

  useEffect(() => {
    mindmapGeneration.refreshActiveTask().catch(() => undefined);
  }, [activeDocId]);

  async function generate() {
    if (
      !activeDocId ||
      doc?.status !== "ready" ||
      user?.quota_status === "exceeded"
    )
      return;
    setStreaming(true);
    setError("");
    setContent("");
    setTree(null);
    setArtifactId(null);
    setFormat(null);
    try {
      const task = await apiFetch<
        | GenerationTask<{
            mindmap_id?: string;
            format?: "tree_json" | "markdown";
            schema_version?: number;
            tree?: MindmapTree;
            content?: string;
          }>
        | { task_id: string; status: string }
      >("/mindmap/jobs", {
        method: "POST",
        body: JSON.stringify({ doc_id: activeDocId, format: "tree_json" }),
      });
      mindmapGeneration.watch(task);
      await loadDocumentStatuses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "心智圖生成失敗");
    } finally {
      setStreaming(false);
    }
  }

  async function expandNode(nodeId: string) {
    if (
      !artifactId ||
      format !== "tree_json" ||
      user?.quota_status === "exceeded"
    )
      return;
    setExpandingNodeId(nodeId);
    setError("");
    try {
      for await (const event of streamFetch(
        `/mindmap/${artifactId}/nodes/${nodeId}/expand/stream`,
        { max_children: 5 },
      )) {
        if (event.type === "mindmap_patch") {
          setTree(event.data.tree);
          setContent(event.data.content);
        } else if (event.type === "error") {
          setError(event.message);
        }
      }
      await loadDocumentStatuses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "節點展開失敗");
    } finally {
      setExpandingNodeId(null);
    }
  }

  function selectDocument(nextDocId: string) {
    setSelectedDocId(nextDocId);
    navigate(`/mindmap/${nextDocId}`);
  }

  function handleDocumentRowKey(
    event: KeyboardEvent<HTMLDivElement>,
    nextDocId: string,
  ) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectDocument(nextDocId);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">心智圖</h1>
          <p className="mt-1 text-sm text-zinc-500">
            選擇文件後查看或產生階層心智圖
          </p>
        </div>
        <LoadingButton
          className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          onClick={generate}
          disabled={
            streaming ||
            !activeDocId ||
            doc?.status !== "ready" ||
            mindmapGeneration.active ||
            user?.quota_status === "exceeded"
          }
          loading={streaming || mindmapGeneration.active}
          loadingText="生成中"
          icon={<Wand2 size={16} />}
        >
          {activeStatus?.has_mindmap ? "重新生成心智圖" : "生成心智圖"}
        </LoadingButton>
      </div>
      <AIGeneratedBadge />
      <GenerationTaskStatus
        task={mindmapGeneration.task}
        error={mindmapGeneration.error}
        title="心智圖生成任務"
      />
      {error && (
        <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}
      <div className="space-y-4">
        <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-zinc-200 px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-zinc-900">
                  選擇文件
                </h2>
                {loadingList && (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-200 border-t-indigo-600" />
                )}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                {documentStatuses.length} 個可用文件，點選後在下方全寬畫布查看
              </p>
            </div>
            {doc && (
              <div className="min-w-0 text-sm xl:text-right">
                <div className="truncate font-medium text-zinc-900">
                  {doc.filename}
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500 xl:justify-end">
                  <span>
                    {doc.page_count ?? 0} 頁 · {doc.chunk_count ?? 0} chunks
                  </span>
                  {activeStatus && (
                    <span
                      className={[
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                        activeStatus.has_mindmap
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-zinc-100 text-zinc-600",
                      ].join(" ")}
                    >
                      {activeStatus.has_mindmap ? "已有心智圖" : "尚未生成"}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
          <div className="overflow-x-auto px-5 py-4">
            <div className="flex min-w-full gap-3">
              {documentStatuses.map((item) => {
                const itemDoc = item.document;
                const selected = itemDoc.id === activeDocId;
                return (
                  <div
                    key={itemDoc.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => selectDocument(itemDoc.id)}
                    onKeyDown={(event) =>
                      handleDocumentRowKey(event, itemDoc.id)
                    }
                    className={[
                      "grid w-[280px] shrink-0 cursor-pointer gap-3 rounded-lg border px-4 py-3 text-sm outline-none transition hover:border-indigo-200 hover:bg-indigo-50/40 focus-visible:ring-2 focus-visible:ring-indigo-500",
                      selected
                        ? "border-indigo-300 bg-indigo-50 shadow-sm"
                        : "border-zinc-200 bg-white",
                    ].join(" ")}
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <FileText
                        size={18}
                        className="mt-0.5 shrink-0 text-zinc-500"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium text-zinc-900">
                          {itemDoc.filename}
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {itemDoc.page_count ?? 0} 頁 ·{" "}
                          {itemDoc.chunk_count ?? 0} chunks
                          {itemDoc.user_id !== user?.id ? " · 課程共享" : ""}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={documentStatusClass(itemDoc.status)}>
                        {documentStatusLabel(itemDoc.status)}
                      </span>
                      {item.has_mindmap ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                          <CheckCircle2 size={13} />
                          已有心智圖
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600">
                          <GitBranch size={13} />
                          尚未生成
                        </span>
                      )}
                      {item.updated_at && (
                        <span className="text-xs text-zinc-500">
                          更新 {formatDateTime(item.updated_at)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
              {documentStatuses.length === 0 && (
                <div className="flex min-h-28 min-w-full items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-zinc-50 px-5 text-center text-sm text-zinc-500">
                  尚無可用文件
                </div>
              )}
            </div>
          </div>
        </section>
        <section className="min-w-0">
          {content ? (
            <div className="space-y-5">
              <MindmapCanvas
                tree={tree}
                markdown={content}
                artifactId={artifactId ?? undefined}
                canAiExpand={
                  format === "tree_json" && user?.quota_status !== "exceeded"
                }
                expandingNodeId={expandingNodeId ?? undefined}
                onAiExpand={expandNode}
              />
              <details className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
                <summary className="cursor-pointer text-sm font-medium text-zinc-700">
                  查看 Markdown 原文
                </summary>
                <div className="mt-4">
                  <MarkdownContent>{content}</MarkdownContent>
                </div>
              </details>
            </div>
          ) : (
            <div className="flex min-h-[520px] items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-white px-4 text-center text-sm text-zinc-500 shadow-sm">
              <div>
                <GitBranch size={22} className="mx-auto mb-2 text-zinc-400" />
                {activeDocId
                  ? doc?.status === "ready"
                    ? "這份文件尚無心智圖"
                    : "文件處理完成後才能生成心智圖"
                  : "請先選擇文件"}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function treeToMarkdown(tree: MindmapTree) {
  const lines = [`# ${tree.root.title || tree.title}`];
  function walk(nodes: MindmapTree["root"]["children"], depth: number) {
    for (const node of nodes) {
      if (depth === 1) lines.push(`## ${node.title}`);
      else lines.push(`${"  ".repeat(depth - 2)}- ${node.title}`);
      walk(node.children, depth + 1);
    }
  }
  walk(tree.root.children, 1);
  return lines.join("\n");
}

function documentStatusLabel(status: string) {
  if (status === "ready") return "Ready";
  if (status === "uploading") return "上傳中";
  if (status === "converting") return "轉換中";
  if (status === "ocr_processing") return "OCR 中";
  if (status === "embedding") return "索引中";
  if (status === "error") return "錯誤";
  return status;
}

function documentStatusClass(status: string) {
  const base = "inline-flex rounded-full px-2 py-1 text-xs font-medium";
  if (status === "ready") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "error") return `${base} bg-red-50 text-red-700`;
  if (["uploading", "converting", "ocr_processing", "embedding"].includes(status))
    return `${base} bg-amber-50 text-amber-700`;
  return `${base} bg-zinc-100 text-zinc-600`;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
