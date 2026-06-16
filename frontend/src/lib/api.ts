export const BASE_URL = import.meta.env.VITE_API_URL ?? "/api"

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export interface User {
  id: string
  username: string
  email: string
  role: string
  quota_mb: number
  token_quota: number
  is_active: number
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface DocumentItem {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: string
  page_count: number | null
  chunk_count: number | null
  error_msg: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id?: string
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
  created_at?: string
}

export interface ChatSession {
  id: string
  title: string | null
  doc_ids: string[]
  mode: string
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

export interface Citation {
  index: number
  doc_id: string
  filename: string
  page: number
  chunk_index: number
  distance: number
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token")
  const headers = new Headers(options.headers)
  const isFormData = options.body instanceof FormData
  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  })
  if (res.status === 401 && path !== "/auth/refresh") {
    const refreshed = await refreshToken()
    if (refreshed) return apiFetch<T>(path, options)
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new ApiError(401, "Unauthorized")
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new ApiError(res.status, err.detail ?? "Request failed")
  }
  return res.json() as Promise<T>
}

export async function refreshToken(): Promise<boolean> {
  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) return false
  const data = (await res.json()) as AuthResponse
  localStorage.setItem("access_token", data.access_token)
  return true
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append("file", file)
  return apiFetch<T>(path, { method: "POST", body: form })
}
