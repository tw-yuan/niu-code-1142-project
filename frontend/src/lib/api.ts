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
  token_used_this_month: number
  quota_percent: number
  quota_status: "ok" | "warning" | "exceeded"
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
  course_id?: string | null
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
  scope?: "personal" | "course"
  distance: number
}

export interface FlashcardItem {
  id: string
  doc_id: string | null
  front: string
  back: string
  source_page: number | null
  repetition: number
  ease_factor: number
  interval_days: number
  next_review: string
  created_at: string
}

export interface QuizItem {
  id: string
  title: string
  doc_ids: string[]
  config: Record<string, unknown>
  questions: Array<Record<string, any>>
  created_at: string
}

export interface NoteItem {
  id: string
  doc_id: string | null
  session_id: string | null
  content: string
  source_page: number | null
  source_type: string | null
  created_at: string
  updated_at: string
}

export interface GoalItem {
  id: string
  doc_id: string
  title: string
  target_date: string
  focus_hint: string | null
  status: "active" | "completed" | "abandoned"
  created_at: string
}

export interface CourseItem {
  id: string
  owner_id: string
  title: string
  description: string | null
  join_code: string | null
  role: string
  is_active: number
  created_at: string
  documents?: Array<Pick<DocumentItem, "id" | "filename" | "status" | "page_count" | "chunk_count" | "created_at">>
}

export interface CostStats {
  today: { total_usd: number; by_feature: Record<string, number> }
  this_month: { total_usd: number; by_feature: Record<string, number> }
  top_users: { user_id: string; username: string; total_usd: number }[]
  daily_series: { date: string; total_usd: number }[]
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
    throw new ApiError(res.status, errorMessage(err))
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

function errorMessage(err: any) {
  if (typeof err?.detail === "string") return err.detail
  if (typeof err?.detail?.message === "string") return err.detail.message
  if (typeof err?.message === "string") return err.message
  return "Request failed"
}
