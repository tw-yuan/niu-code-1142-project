import { useState } from "react"
import { Download, Trash2 } from "lucide-react"
import { BASE_URL, apiFetch, refreshToken } from "../lib/api"
import { useAuthStore } from "../store/auth"

export function SettingsPage() {
  const { user, logout } = useAuthStore()
  const [code, setCode] = useState("")
  const [input, setInput] = useState("")
  const [exportReady, setExportReady] = useState(false)
  const [message, setMessage] = useState("")

  async function requestExport() {
    const result = await apiFetch<{ expires_at: string }>("/auth/me/export-request", { method: "POST" })
    setExportReady(true)
    setMessage(`匯出檔有效至 ${result.expires_at.slice(0, 19)}`)
  }

  async function requestDelete() {
    const result = await apiFetch<{ confirmation_code: string; deletion_scheduled_at: string }>("/auth/me/delete-request", { method: "POST" })
    setCode(result.confirmation_code)
    setMessage(`已建立刪除請求，預計清除日 ${result.deletion_scheduled_at.slice(0, 10)}`)
  }

  async function confirmDelete() {
    if (!input || input !== code) return
    await apiFetch("/auth/me/delete-confirm", {
      method: "POST",
      body: JSON.stringify({ confirmation_code: input }),
    })
    await logout()
    window.location.href = "/login"
  }

  async function downloadExport() {
    const blob = await loadAuthorizedBlob("/auth/me/export-download")
    downloadBlob(blob, "learnai-export.zip")
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">設定</h1>
        <p className="mt-1 text-sm text-zinc-500">{user?.email}</p>
      </div>
      {message && <div className="mb-4 rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-700">{message}</div>}
      <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="mb-2 font-semibold">資料匯出</h2>
        <p className="mb-4 text-sm leading-6 text-zinc-600">匯出 profile、文件清單、對話、閃卡、測驗紀錄與筆記。ZIP 有效期 24 小時。</p>
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700" onClick={requestExport}>
            <Download size={16} />
            產生匯出檔
          </button>
          {exportReady && (
            <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50" onClick={downloadExport}>
              下載 ZIP
            </button>
          )}
        </div>
      </section>
      <section className="rounded-lg border border-red-200 bg-white p-5 shadow-sm">
        <h2 className="mb-2 flex items-center gap-2 font-semibold text-red-700">
          <Trash2 size={18} />
          危險區域
        </h2>
        <p className="mb-4 text-sm leading-6 text-zinc-600">確認後帳號會立即停用，30 天後由系統清除 DB、檔案與向量資料。</p>
        <button className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50" onClick={requestDelete}>
          申請刪除帳號
        </button>
        {code && (
          <div className="mt-4 rounded-md bg-red-50 p-4">
            <div className="mb-2 text-sm text-red-700">確認碼：{code}</div>
            <input className="mb-2 w-full rounded-lg border border-red-200 px-3 py-2 text-sm" value={input} onChange={(event) => setInput(event.target.value)} placeholder="輸入確認碼" />
            <button className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300" disabled={input !== code} onClick={confirmDelete}>
              確認停用帳號
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

async function loadAuthorizedBlob(path: string): Promise<Blob> {
  let res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() })
  if (res.status === 401 && (await refreshToken())) {
    res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() })
  }
  if (!res.ok) throw new Error("Failed to load file")
  return res.blob()
}

function authHeaders() {
  const token = localStorage.getItem("access_token")
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
