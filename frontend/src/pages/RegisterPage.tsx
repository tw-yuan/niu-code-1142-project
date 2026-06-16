import { FormEvent, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { UserPlus } from "lucide-react"
import { useAuthStore } from "../store/auth"

export function RegisterPage() {
  const navigate = useNavigate()
  const register = useAuthStore((state) => state.register)
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError("")
    try {
      await register(username, email, password)
      navigate("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "註冊失敗")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-6 shadow-sm"
      >
        <div className="mb-6">
          <div className="text-2xl font-semibold">LearnAI</div>
          <div className="mt-1 text-sm text-zinc-500">建立新帳號</div>
        </div>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">使用者名稱</span>
          <input
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-indigo-600"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">Email</span>
          <input
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-indigo-600"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">密碼</span>
          <input
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-indigo-600"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </label>
        {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
        <button
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          disabled={loading}
        >
          <UserPlus size={16} />
          註冊
        </button>
        <div className="mt-4 text-center text-sm text-zinc-500">
          已有帳號？{" "}
          <Link className="font-medium text-indigo-600" to="/login">
            登入
          </Link>
        </div>
      </form>
    </main>
  )
}

