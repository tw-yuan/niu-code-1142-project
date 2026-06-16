import { Info } from "lucide-react"
import { useState } from "react"

export function AIGeneratedBadge({
  variant = "default",
  text = "由 AI 生成，內容僅供參考，請自行驗證",
}: {
  variant?: "default" | "inline"
  text?: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className={variant === "inline" ? "mt-2" : "mb-4"}>
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-800"
        onClick={() => setOpen((value) => !value)}
        title="AI 生成內容提醒"
      >
        <Info size={14} />
        {text}
      </button>
      {open && (
        <div className="mt-2 max-w-xl rounded-md border border-amber-200 bg-white px-3 py-2 text-xs leading-5 text-zinc-600">
          AI 可能產生錯誤或遺漏。請搭配引用頁面、原始文件與課堂資料確認內容。
        </div>
      )}
    </div>
  )
}
