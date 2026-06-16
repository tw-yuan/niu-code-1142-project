import { FormEvent, useEffect, useState } from "react"
import { Download, Save, ShieldCheck, Trash2 } from "lucide-react"
import { BASE_URL, apiFetch, refreshToken, User } from "../lib/api"
import { useAuthStore } from "../store/auth"

export function SettingsPage() {
  const { user, logout, setUser } = useAuthStore()
  const [username, setUsername] = useState(user?.username ?? "")
  const [email, setEmail] = useState(user?.email ?? "")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [code, setCode] = useState("")
  const [input, setInput] = useState("")
  const [exportReady, setExportReady] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    setUsername(user?.username ?? "")
    setEmail(user?.email ?? "")
  }, [user?.username, user?.email])

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    setError("")
    const updated = await apiFetch<User>("/auth/me", {
      method: "PUT",
      body: JSON.stringify({ username: username.trim(), email: email.trim() }),
    })
    setUser(updated)
    setMessage("帳號資料已更新")
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault()
    setError("")
    await apiFetch("/auth/me/password", {
      method: "PUT",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
    setCurrentPassword("")
    setNewPassword("")
    setMessage("密碼已更新，請於下次操作時重新登入")
  }

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
      {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
      <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 font-semibold">個人資料</h2>
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => saveProfile(event).catch((err) => setError(err instanceof Error ? err.message : "更新失敗"))}>
          <label className="text-sm">
            <span className="mb-1 block text-zinc-600">Username</span>
            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2" value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-zinc-600">Email</span>
            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <div className="sm:col-span-2">
            <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
              <Save size={16} />
              儲存個人資料
            </button>
          </div>
        </form>
      </section>
      <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 flex items-center gap-2 font-semibold">
          <ShieldCheck size={18} />
          密碼
        </h2>
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => changePassword(event).catch((err) => setError(err instanceof Error ? err.message : "密碼更新失敗"))}>
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} placeholder="目前密碼" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="新密碼" />
          <div className="sm:col-span-2">
            <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50" disabled={!currentPassword || newPassword.length < 8}>
              更新密碼
            </button>
          </div>
        </form>
      </section>
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
