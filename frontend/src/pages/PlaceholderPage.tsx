import { Construction } from "lucide-react"

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="rounded-lg border border-zinc-200 bg-white p-8 shadow-sm">
        <Construction className="mb-4 text-zinc-500" size={28} />
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-zinc-500">此功能的後端 API 已保留，前端操作介面會在下一輪補齊。</p>
      </div>
    </div>
  )
}

