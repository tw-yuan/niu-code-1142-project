import { useCallback, useEffect, useState } from "react";
import { GitBranch, Wand2 } from "lucide-react";
import { useParams } from "react-router-dom";
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge";
import { GenerationTaskStatus } from "../components/app/GenerationTaskPanel";
import { LoadingButton } from "../components/app/LoadingButton";
import { MarkdownContent } from "../components/app/MarkdownContent";
import { MindmapCanvas } from "../components/app/MindmapCanvas";
import {
  apiFetch,
  DocumentItem,
  GenerationTask,
  MindmapResponse,
  MindmapTree,
} from "../lib/api";
import { useGenerationTask } from "../lib/generation";
import { streamFetch } from "../lib/stream";
import { useAuthStore } from "../store/auth";

export function MindmapPage() {
  const { docId } = useParams();
  const user = useAuthStore((state) => state.user);
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [content, setContent] = useState("");
  const [tree, setTree] = useState<MindmapTree | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [format, setFormat] = useState<"tree_json" | "markdown" | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);
  const [error, setError] = useState("");
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
        return;
      }
      if (docId) {
        const data = await apiFetch<MindmapResponse>(`/mindmap/${docId}`);
        setContent(data.content);
        setTree(data.tree);
        setArtifactId(data.id);
        setFormat(data.format);
      }
    },
    [docId],
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
    ) => task.input.doc_id === docId,
    [docId],
  );
  const mindmapGeneration = useGenerationTask<{
    mindmap_id?: string;
    format?: "tree_json" | "markdown";
    schema_version?: number;
    tree?: MindmapTree;
    content?: string;
  }>("mindmap", handleMindmapGenerated, matchMindmapTask);

  useEffect(() => {
    if (!docId) return;
    apiFetch<DocumentItem>(`/documents/${docId}`)
      .then(setDoc)
      .catch(() => undefined);
    apiFetch<MindmapResponse>(`/mindmap/${docId}`)
      .then((data) => {
        setContent(data.content);
        setTree(data.tree);
        setArtifactId(data.id);
        setFormat(data.format);
      })
      .catch(() => undefined);
  }, [docId]);

  useEffect(() => {
    mindmapGeneration.refreshActiveTask().catch(() => undefined);
  }, [docId]);

  async function generate() {
    if (!docId || user?.quota_status === "exceeded") return;
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
        body: JSON.stringify({ doc_id: docId, format: "tree_json" }),
      });
      mindmapGeneration.watch(task);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "節點展開失敗");
    } finally {
      setExpandingNodeId(null);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">心智圖</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {doc?.filename ?? "選定文件"}
          </p>
        </div>
        <LoadingButton
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          onClick={generate}
          disabled={
            streaming ||
            mindmapGeneration.active ||
            user?.quota_status === "exceeded"
          }
          loading={streaming || mindmapGeneration.active}
          loadingText="生成中"
          icon={<Wand2 size={16} />}
        >
          生成心智圖
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
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
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
            <details className="rounded-lg border border-zinc-200 p-4">
              <summary className="cursor-pointer text-sm font-medium text-zinc-700">
                查看 Markdown 原文
              </summary>
              <div className="mt-4">
                <MarkdownContent>{content}</MarkdownContent>
              </div>
            </details>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <GitBranch size={16} />
            尚無心智圖
          </div>
        )}
      </section>
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
