import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  CircleDot,
  GitBranch,
  Layers,
  LocateFixed,
  Maximize2,
  Minus,
  Plus,
  Search,
  Sparkles,
} from "lucide-react";
import { MindmapNode, MindmapTree } from "../../lib/api";
import { LoadingButton } from "./LoadingButton";
import { MathText } from "./MathText";

interface LayoutNode extends MindmapNode {
  x: number;
  y: number;
  width: number;
  height: number;
  hiddenChildCount: number;
}

interface Props {
  tree: MindmapTree | null;
  markdown?: string;
  artifactId?: string;
  canAiExpand?: boolean;
  expandingNodeId?: string;
  onAiExpand?: (nodeId: string) => void;
}

const NODE_WIDTH = 230;
const NODE_HEIGHT = 60;
const X_GAP = 112;
const Y_GAP = 24;
const MAX_ZOOM = 1.6;
const MIN_ZOOM = 0.5;

export function MindmapCanvas({
  tree,
  markdown = "",
  artifactId,
  canAiExpand = false,
  expandingNodeId,
  onAiExpand,
}: Props) {
  const parsedTree = useMemo(
    () => tree ?? markdownToTree(markdown),
    [tree, markdown],
  );
  const [zoom, setZoom] = useState(1);
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const [selectedId, setSelectedId] = useState("root");
  const [query, setQuery] = useState("");
  const [showOutline, setShowOutline] = useState(false);

  const searchMatches = useMemo(
    () => findMatches(parsedTree, query),
    [parsedTree, query],
  );
  const layout = useMemo(
    () =>
      parsedTree
        ? layoutTree(parsedTree.root, collapsed, searchMatches.ancestorIds)
        : null,
    [parsedTree, collapsed, searchMatches.ancestorIds],
  );
  const selected = useMemo(
    () =>
      parsedTree
        ? (findNode(parsedTree.root, selectedId) ?? parsedTree.root)
        : null,
    [parsedTree, selectedId],
  );

  if (!parsedTree || !layout || layout.nodes.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-sm text-zinc-500">
        目前內容無法解析成節點
      </div>
    );
  }

  function setCollapsedDepth(depth: number) {
    if (!parsedTree) return;
    setCollapsed(collapsedAfterDepth(parsedTree.root, depth));
  }

  function toggleNode(node: MindmapNode) {
    if (!hasChildren(node)) return;
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(node.id)) next.delete(node.id);
      else next.add(node.id);
      return next;
    });
  }

  const canExpandSelected =
    Boolean(artifactId && canAiExpand && selected && selected.id !== "root") &&
    (selected?.expandable ?? true) &&
    (selected?.depth ?? 0) < 5;

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white">
      <div className="flex flex-col gap-2 border-b border-zinc-200 bg-white p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <GitBranch size={17} className="shrink-0 text-indigo-600" />
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-zinc-800">
              階層心智圖
            </div>
            <div className="text-xs text-zinc-500">
              預設聚焦骨架，可逐層展開細節
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search
              size={15}
              className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-zinc-400"
            />
            <input
              className="h-9 w-44 rounded-md border border-zinc-200 bg-white pl-8 pr-3 text-sm outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
              placeholder="搜尋節點"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <IconButton
            label="展開到第 2 層"
            onClick={() => setCollapsedDepth(2)}
          >
            <Layers size={16} />
          </IconButton>
          <IconButton label="全部收合" onClick={() => setCollapsedDepth(1)}>
            <ChevronsDownUp size={16} />
          </IconButton>
          <IconButton label="全部展開" onClick={() => setCollapsed(new Set())}>
            <ChevronsUpDown size={16} />
          </IconButton>
          <IconButton
            label="縮小"
            onClick={() => setZoom((value) => Math.max(MIN_ZOOM, value - 0.1))}
          >
            <Minus size={16} />
          </IconButton>
          <IconButton label="重設縮放" onClick={() => setZoom(1)}>
            <Maximize2 size={16} />
          </IconButton>
          <IconButton
            label="放大"
            onClick={() => setZoom((value) => Math.min(MAX_ZOOM, value + 0.1))}
          >
            <Plus size={16} />
          </IconButton>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm text-zinc-700 hover:bg-zinc-50 lg:hidden"
            onClick={() => setShowOutline((value) => !value)}
          >
            <LocateFixed size={16} />
            大綱
          </button>
        </div>
      </div>

      {query.trim() && (
        <div className="border-b border-zinc-200 bg-indigo-50 px-3 py-2 text-xs text-indigo-700">
          找到 {searchMatches.ids.size} 個節點，已自動展開所在路徑
        </div>
      )}

      <div className="grid min-h-0 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div
          className={[
            showOutline ? "hidden lg:block" : "block",
            "min-w-0 bg-zinc-50",
          ].join(" ")}
        >
          <div className="h-[min(70vh,720px)] min-h-[420px] overflow-auto p-4">
            <svg
              width={layout.width * zoom}
              height={layout.height * zoom}
              viewBox={`0 0 ${layout.width} ${layout.height}`}
              role="img"
              aria-label="可展開階層心智圖"
              className="min-w-full"
            >
              <defs>
                <filter
                  id="mindmap-shadow"
                  x="-10%"
                  y="-10%"
                  width="120%"
                  height="120%"
                >
                  <feDropShadow
                    dx="0"
                    dy="2"
                    stdDeviation="3"
                    floodOpacity="0.11"
                  />
                </filter>
              </defs>
              {layout.edges.map((edge) => (
                <path
                  key={`${edge.from.id}-${edge.to.id}`}
                  d={edgePath(edge.from, edge.to)}
                  fill="none"
                  stroke="#c4c4cc"
                  strokeWidth={2}
                  strokeLinecap="round"
                />
              ))}
              {layout.nodes.map((node) => {
                const isRoot = node.id === "root";
                const isSelected = node.id === selectedId;
                const isMatch = searchMatches.ids.has(node.id);
                const collapsedNode =
                  collapsed.has(node.id) && hasChildren(node);
                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                  >
                    <rect
                      width={node.width}
                      height={node.height}
                      rx={8}
                      fill={
                        isRoot ? "#4f46e5" : isMatch ? "#eef2ff" : "#ffffff"
                      }
                      stroke={
                        isSelected ? "#4f46e5" : isMatch ? "#818cf8" : "#d4d4d8"
                      }
                      strokeWidth={isSelected ? 2.5 : 1}
                      filter="url(#mindmap-shadow)"
                    />
                    {hasChildren(node) && (
                      <g
                        className="cursor-pointer"
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleNode(node);
                        }}
                      >
                        <circle
                          cx={18}
                          cy={node.height / 2}
                          r={13}
                          fill={isRoot ? "#4338ca" : "#f4f4f5"}
                        />
                        {collapsedNode ? (
                          <ChevronRight
                            x={10}
                            y={node.height / 2 - 8}
                            size={16}
                            color={isRoot ? "#ffffff" : "#52525b"}
                          />
                        ) : (
                          <ChevronDown
                            x={10}
                            y={node.height / 2 - 8}
                            size={16}
                            color={isRoot ? "#ffffff" : "#52525b"}
                          />
                        )}
                      </g>
                    )}
                    <g
                      className="cursor-pointer"
                      onClick={() => {
                        setSelectedId(node.id);
                      }}
                    >
                      <foreignObject
                        x={hasChildren(node) ? 36 : 12}
                        y={0}
                        width={node.width - (hasChildren(node) ? 48 : 24)}
                        height={node.height}
                      >
                        <div
                          className={[
                            "flex h-full flex-col justify-center",
                            isRoot ? "text-white" : "text-zinc-800",
                          ].join(" ")}
                        >
                          <div className="line-clamp-2 text-sm font-semibold leading-5">
                            <MathText>{node.title}</MathText>
                          </div>
                          {!isRoot && (
                            <div
                              className={[
                                "mt-0.5 flex items-center gap-1 text-[11px]",
                                typeColor(node.type),
                              ].join(" ")}
                            >
                              <CircleDot size={10} />
                              <span>{typeLabel(node.type)}</span>
                              {node.hiddenChildCount > 0 && (
                                <span className="text-zinc-500">
                                  +{node.hiddenChildCount}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </foreignObject>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <aside
          className={[
            showOutline ? "block" : "hidden lg:block",
            "border-l border-zinc-200 bg-white",
          ].join(" ")}
        >
          <div className="h-[min(70vh,720px)] min-h-[420px] overflow-auto">
            <div className="border-b border-zinc-200 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                目前節點
              </div>
              <h2 className="mt-1 text-base font-semibold leading-7 text-zinc-900">
                <MathText>{selected?.title ?? ""}</MathText>
              </h2>
              {selected?.summary && (
                <div className="mt-2 text-sm leading-6 text-zinc-600">
                  <MathText>{selected.summary}</MathText>
                </div>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-600">
                  第 {selected?.depth ?? 0} 層
                </span>
                <span className="rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-600">
                  {typeLabel(selected?.type)}
                </span>
              </div>
              {canExpandSelected && (
                <LoadingButton
                  className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                  disabled={expandingNodeId === selected?.id}
                  loading={expandingNodeId === selected?.id}
                  loadingText="展開中"
                  icon={<Sparkles size={16} />}
                  onClick={() => selected && onAiExpand?.(selected.id)}
                >
                  AI 往下展開
                </LoadingButton>
              )}
            </div>
            {selected?.source_refs && selected.source_refs.length > 0 && (
              <div className="border-b border-zinc-200 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
                  來源
                </div>
                <div className="space-y-2">
                  {selected.source_refs.map((ref, index) => (
                    <div
                      key={`${ref.page_num}-${ref.chunk_index}-${index}`}
                      className="rounded-md border border-zinc-200 px-3 py-2 text-xs text-zinc-600"
                    >
                      {ref.page_num ? `第 ${ref.page_num} 頁` : "來源頁未標示"}
                      {ref.label ? ` · ${ref.label}` : ""}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="p-4">
              <div className="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-400">
                大綱
              </div>
              <OutlineTree
                node={parsedTree.root}
                selectedId={selectedId}
                collapsed={collapsed}
                onSelect={setSelectedId}
                onToggle={toggleNode}
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100"
      title={label}
      aria-label={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function OutlineTree({
  node,
  selectedId,
  collapsed,
  onSelect,
  onToggle,
}: {
  node: MindmapNode;
  selectedId: string;
  collapsed: Set<string>;
  onSelect: (id: string) => void;
  onToggle: (node: MindmapNode) => void;
}) {
  const childrenVisible = !collapsed.has(node.id);
  return (
    <div>
      <div className="flex items-center gap-1 py-1">
        <button
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-zinc-500 hover:bg-zinc-100"
          onClick={() => onToggle(node)}
          disabled={!hasChildren(node)}
          title={collapsed.has(node.id) ? "展開" : "收合"}
        >
          {hasChildren(node) ? (
            collapsed.has(node.id) ? (
              <ChevronRight size={15} />
            ) : (
              <ChevronDown size={15} />
            )
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300" />
          )}
        </button>
        <button
          className={[
            "min-w-0 flex-1 rounded px-2 py-1 text-left text-sm",
            selectedId === node.id
              ? "bg-indigo-50 font-medium text-indigo-700"
              : "text-zinc-700 hover:bg-zinc-50",
          ].join(" ")}
          onClick={() => onSelect(node.id)}
        >
          <span className="line-clamp-1">
            <MathText>{node.title}</MathText>
          </span>
        </button>
      </div>
      {childrenVisible && node.children.length > 0 && (
        <div className="ml-5 border-l border-zinc-200 pl-2">
          {node.children.map((child) => (
            <OutlineTree
              key={child.id}
              node={child}
              selectedId={selectedId}
              collapsed={collapsed}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function markdownToTree(markdown: string): MindmapTree | null {
  if (!markdown.trim()) return null;
  const root: MindmapNode = {
    id: "root",
    title: "心智圖",
    summary: null,
    depth: 0,
    order: 0,
    expandable: false,
    children_loaded: true,
    children: [],
    source_refs: [],
  };
  const stack: Array<{ markdownDepth: number; node: MindmapNode }> = [
    { markdownDepth: 0, node: root },
  ];
  let counter = 0;
  let bulletBaseDepth = 2;

  for (const raw of markdown.split("\n")) {
    const trimmed = raw.trim();
    if (!trimmed || trimmed.startsWith("```")) continue;
    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    let markdownDepth = 0;
    let label = "";
    if (heading) {
      markdownDepth = heading[1].length;
      label = cleanLabel(heading[2]);
      bulletBaseDepth = markdownDepth + 1;
    } else {
      const bullet = raw.match(/^(\s*)([-*+]|\d+\.)\s+(.+)$/);
      if (!bullet) continue;
      markdownDepth = bulletBaseDepth + Math.floor(bullet[1].length / 2);
      label = cleanLabel(bullet[3]);
    }
    if (
      markdownDepth === 1 &&
      root.title === "心智圖" &&
      root.children.length === 0
    ) {
      root.title = label;
      continue;
    }
    while (
      stack.length > 1 &&
      stack[stack.length - 1].markdownDepth >= markdownDepth
    )
      stack.pop();
    const parent = stack[stack.length - 1].node;
    const node: MindmapNode = {
      id: `legacy-${counter++}`,
      title: label,
      summary: null,
      depth: parent.depth + 1,
      order: parent.children.length,
      type: "concept",
      expandable: false,
      children_loaded: true,
      children: [],
      source_refs: [],
    };
    parent.children.push(node);
    parent.expandable = true;
    stack.push({ markdownDepth, node });
  }

  return {
    schema_version: 1,
    title: root.title,
    doc_id: "",
    root,
  };
}

function layoutTree(
  root: MindmapNode,
  collapsed: Set<string>,
  forcedOpen: Set<string>,
) {
  const positioned: LayoutNode[] = [];
  const edges: Array<{ from: LayoutNode; to: LayoutNode }> = [];
  let cursorY = 28;

  function visit(node: MindmapNode, depth: number): LayoutNode {
    const shouldCollapse = collapsed.has(node.id) && !forcedOpen.has(node.id);
    const visibleChildren = shouldCollapse ? [] : node.children;
    const children = visibleChildren.map((child) => visit(child, depth + 1));
    const subtreeTop = children.length ? children[0].y : cursorY;
    const subtreeBottom = children.length
      ? children[children.length - 1].y
      : cursorY;
    const y = children.length ? (subtreeTop + subtreeBottom) / 2 : cursorY;
    if (!children.length) cursorY += NODE_HEIGHT + Y_GAP;
    const layoutNode: LayoutNode = {
      ...node,
      x: 28 + depth * (NODE_WIDTH + X_GAP),
      y,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      hiddenChildCount: Math.max(0, node.children.length - children.length),
    };
    positioned.push(layoutNode);
    for (const child of children) edges.push({ from: layoutNode, to: child });
    return layoutNode;
  }

  visit(root, 0);
  const maxX = Math.max(
    ...positioned.map((node) => node.x + node.width),
    NODE_WIDTH,
  );
  const maxY = Math.max(
    ...positioned.map((node) => node.y + node.height),
    NODE_HEIGHT,
  );
  return { nodes: positioned, edges, width: maxX + 56, height: maxY + 56 };
}

function collapsedAfterDepth(root: MindmapNode, depth: number) {
  const next = new Set<string>();
  function visit(node: MindmapNode) {
    if (node.depth >= depth && hasChildren(node)) next.add(node.id);
    node.children.forEach(visit);
  }
  visit(root);
  return next;
}

function findMatches(tree: MindmapTree | null, query: string) {
  const ids = new Set<string>();
  const ancestorIds = new Set<string>();
  const normalized = query.trim().toLowerCase();
  if (!tree || !normalized) return { ids, ancestorIds };

  function visit(node: MindmapNode, ancestors: string[]) {
    const text = `${node.title} ${node.summary ?? ""}`.toLowerCase();
    if (text.includes(normalized)) {
      ids.add(node.id);
      ancestors.forEach((id) => ancestorIds.add(id));
    }
    node.children.forEach((child) => visit(child, [...ancestors, node.id]));
  }
  visit(tree.root, []);
  return { ids, ancestorIds };
}

function findNode(node: MindmapNode, id: string): MindmapNode | null {
  if (node.id === id) return node;
  for (const child of node.children) {
    const found = findNode(child, id);
    if (found) return found;
  }
  return null;
}

function hasChildren(node: MindmapNode) {
  return node.children.length > 0;
}

function edgePath(from: LayoutNode, to: LayoutNode) {
  const startX = from.x + from.width;
  const startY = from.y + from.height / 2;
  const endX = to.x;
  const endY = to.y + to.height / 2;
  const midX = startX + (endX - startX) / 2;
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function cleanLabel(value: string) {
  return value
    .replace(/\*\*/g, "")
    .replace(/^#+\s*/, "")
    .trim()
    .slice(0, 36);
}

function typeLabel(type?: string) {
  const labels: Record<string, string> = {
    concept: "概念",
    process: "流程",
    example: "例子",
    pitfall: "易錯",
    comparison: "比較",
    formula: "公式",
    application: "應用",
    summary: "摘要",
  };
  return labels[type ?? "concept"] ?? "概念";
}

function typeColor(type?: string) {
  const colors: Record<string, string> = {
    concept: "text-indigo-600",
    process: "text-sky-600",
    example: "text-emerald-600",
    pitfall: "text-red-600",
    comparison: "text-amber-600",
    formula: "text-fuchsia-600",
    application: "text-teal-600",
    summary: "text-zinc-500",
  };
  return colors[type ?? "concept"] ?? "text-zinc-500";
}
