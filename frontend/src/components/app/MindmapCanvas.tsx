import { useMemo, useState } from "react"
import { Maximize2, Minus, Plus } from "lucide-react"

interface TreeNode {
  id: string
  label: string
  children: TreeNode[]
}

interface LayoutNode extends TreeNode {
  x: number
  y: number
  width: number
  height: number
}

interface Props {
  markdown: string
}

const NODE_WIDTH = 220
const NODE_HEIGHT = 56
const X_GAP = 110
const Y_GAP = 28

export function MindmapCanvas({ markdown }: Props) {
  const [zoom, setZoom] = useState(1)
  const tree = useMemo(() => parseMindmap(markdown), [markdown])
  const layout = useMemo(() => (tree ? layoutTree(tree) : null), [tree])

  if (!tree || !layout) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-sm text-zinc-500">
        目前內容無法解析成節點
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50">
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-3 py-2">
        <div className="text-sm font-medium text-zinc-700">節點心智圖</div>
        <div className="flex items-center gap-1">
          <button className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100" title="縮小" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>
            <Minus size={16} />
          </button>
          <button className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100" title="重設縮放" onClick={() => setZoom(1)}>
            <Maximize2 size={16} />
          </button>
          <button className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100" title="放大" onClick={() => setZoom((value) => Math.min(1.6, value + 0.1))}>
            <Plus size={16} />
          </button>
        </div>
      </div>
      <div className="max-h-[70vh] overflow-auto p-4">
        <svg
          width={layout.width * zoom}
          height={layout.height * zoom}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label="心智圖節點圖"
          className="min-w-full"
        >
          <defs>
            <filter id="mindmap-shadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
            </filter>
          </defs>
          {layout.edges.map((edge) => (
            <path
              key={`${edge.from.id}-${edge.to.id}`}
              d={edgePath(edge.from, edge.to)}
              fill="none"
              stroke="#a1a1aa"
              strokeWidth={2}
              strokeLinecap="round"
            />
          ))}
          {layout.nodes.map((node) => (
            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
              <rect
                width={node.width}
                height={node.height}
                rx={8}
                fill={node.id === "root" ? "#4f46e5" : "#ffffff"}
                stroke={node.id === "root" ? "#4f46e5" : "#d4d4d8"}
                filter="url(#mindmap-shadow)"
              />
              <foreignObject width={node.width} height={node.height}>
                <div
                  className={[
                    "flex h-full items-center px-3 text-sm font-medium leading-5",
                    node.id === "root" ? "text-white" : "text-zinc-800",
                  ].join(" ")}
                >
                  <span className="line-clamp-2 break-words">{node.label}</span>
                </div>
              </foreignObject>
            </g>
          ))}
        </svg>
      </div>
    </div>
  )
}

function parseMindmap(markdown: string): TreeNode | null {
  const lines = markdown
    .split("\n")
    .map((line) => line.trimEnd())
    .filter((line) => line.trim() && !line.trim().startsWith("```"))
  const root: TreeNode = { id: "root", label: "心智圖", children: [] }
  const stack: Array<{ depth: number; node: TreeNode }> = [{ depth: 0, node: root }]
  let counter = 0

  for (const raw of lines) {
    const parsed = parseLine(raw)
    if (!parsed) continue
    const node: TreeNode = { id: `node-${counter++}`, label: parsed.label, children: [] }
    while (stack.length > 1 && stack[stack.length - 1].depth >= parsed.depth) stack.pop()
    stack[stack.length - 1].node.children.push(node)
    stack.push({ depth: parsed.depth, node })
  }

  if (root.children.length === 0) return null
  if (root.children.length === 1) {
    return { ...root.children[0], id: "root" }
  }
  return root
}

function parseLine(line: string): { depth: number; label: string } | null {
  const heading = line.match(/^(#{1,6})\s+(.+)$/)
  if (heading) return { depth: heading[1].length, label: cleanLabel(heading[2]) }

  const bullet = line.match(/^(\s*)([-*+]|\d+\.)\s+(.+)$/)
  if (bullet) return { depth: Math.floor(bullet[1].length / 2) + 2, label: cleanLabel(bullet[3]) }

  return null
}

function cleanLabel(value: string) {
  return value.replace(/\*\*/g, "").replace(/^#+\s*/, "").trim()
}

function layoutTree(root: TreeNode) {
  const positioned: LayoutNode[] = []
  const edges: Array<{ from: LayoutNode; to: LayoutNode }> = []
  let cursorY = 24

  function visit(node: TreeNode, depth: number): LayoutNode {
    const children = node.children.map((child) => visit(child, depth + 1))
    const subtreeTop = children.length ? children[0].y : cursorY
    const subtreeBottom = children.length ? children[children.length - 1].y : cursorY
    const y = children.length ? (subtreeTop + subtreeBottom) / 2 : cursorY
    if (!children.length) cursorY += NODE_HEIGHT + Y_GAP

    const layoutNode: LayoutNode = {
      ...node,
      x: 24 + depth * (NODE_WIDTH + X_GAP),
      y,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    }
    positioned.push(layoutNode)
    for (const child of children) edges.push({ from: layoutNode, to: child })
    return layoutNode
  }

  visit(root, 0)
  const maxX = Math.max(...positioned.map((node) => node.x + node.width), NODE_WIDTH)
  const maxY = Math.max(...positioned.map((node) => node.y + node.height), NODE_HEIGHT)
  return { nodes: positioned, edges, width: maxX + 48, height: maxY + 48 }
}

function edgePath(from: LayoutNode, to: LayoutNode) {
  const startX = from.x + from.width
  const startY = from.y + from.height / 2
  const endX = to.x
  const endY = to.y + to.height / 2
  const midX = startX + (endX - startX) / 2
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`
}
