import { BrainCircuit, FileText, MessageSquareText, TrendingUp } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { useEffect, useState } from "react"
import { apiFetch, DocumentItem } from "../lib/api"

export function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])

  useEffect(() => {
    apiFetch<DocumentItem[]>("/documents").then(setDocuments).catch(() => setDocuments([]))
  }, [])

  const ready = documents.filter((doc) => doc.status === "ready").length
  const processing = documents.filter((doc) => doc.status !== "ready" && doc.status !== "error").length

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">儀表板</h1>
        <p className="mt-1 text-sm text-zinc-500">本週學習狀態</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric title="文件總數" value={documents.length} icon={FileText} />
        <Metric title="可用文件" value={ready} icon={TrendingUp} />
        <Metric title="處理中" value={processing} icon={MessageSquareText} />
        <Metric title="待複習" value={0} icon={BrainCircuit} />
      </div>
      <section className="mt-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-semibold">最近文件</h2>
        </div>
        <div className="divide-y divide-zinc-100">
          {documents.slice(0, 6).map((doc) => (
            <div key={doc.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <div className="text-sm font-medium">{doc.filename}</div>
                <div className="text-xs text-zinc-500">{doc.file_type}</div>
              </div>
              <span className="rounded-lg bg-zinc-100 px-2 py-1 text-xs text-zinc-600">{doc.status}</span>
            </div>
          ))}
          {documents.length === 0 && <div className="px-5 py-8 text-sm text-zinc-500">尚無文件</div>}
        </div>
      </section>
    </div>
  )
}

function Metric({
  title,
  value,
  icon: Icon,
}: {
  title: string
  value: number
  icon: LucideIcon
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm text-zinc-500">{title}</span>
        <Icon size={18} className="text-zinc-500" />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  )
}
