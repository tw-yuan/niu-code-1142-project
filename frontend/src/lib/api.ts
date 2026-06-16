export const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  quota_mb: number;
  token_quota: number;
  is_active: number;
  token_used_this_month: number;
  quota_percent: number;
  quota_status: "ok" | "warning" | "exceeded";
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  error_msg: string | null;
  course_status?: "active" | "removed" | string;
  created_at: string;
  updated_at: string;
}

export interface DocumentContent {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  page_count: number | null;
  pages: Array<{ page_num: number; text: string }>;
  content: string;
}

export interface DocumentUploadResult {
  filename: string;
  ok: boolean;
  document: DocumentItem | null;
  error: string | null;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at?: string;
}

export interface ChatSession {
  id: string;
  title: string | null;
  doc_ids: string[];
  course_id?: string | null;
  mode: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface Citation {
  index: number;
  doc_id: string;
  filename: string;
  page: number;
  chunk_index: number;
  scope?: "personal" | "course";
  distance: number;
  snippet?: string;
  retrieval_score?: number | null;
  support_status?: "supported" | "partial" | "unverified" | string;
}

export interface MindmapSourceRef {
  doc_id?: string;
  page_num?: number | null;
  chunk_index?: number | null;
  label?: string | null;
}

export interface MindmapNode {
  id: string;
  title: string;
  summary?: string | null;
  depth: number;
  order: number;
  type?:
    | "concept"
    | "process"
    | "example"
    | "pitfall"
    | "comparison"
    | "formula"
    | "application"
    | "summary"
    | string;
  expandable?: boolean;
  children_loaded?: boolean;
  children: MindmapNode[];
  source_refs?: MindmapSourceRef[];
  parent_id?: string;
}

export interface MindmapTree {
  schema_version: number;
  title: string;
  doc_id: string;
  root: MindmapNode;
  created_at?: string;
  updated_at?: string;
}

export interface MindmapResponse {
  id: string;
  doc_id: string;
  format: "tree_json" | "markdown";
  schema_version: number;
  tree: MindmapTree | null;
  content: string;
}

export interface FlashcardItem {
  id: string;
  doc_id: string | null;
  front: string;
  back: string;
  source_page: number | null;
  repetition: number;
  ease_factor: number;
  interval_days: number;
  next_review: string;
  created_at: string;
}

export interface QuizItem {
  id: string;
  title: string;
  course_id?: string | null;
  doc_ids: string[];
  config: Record<string, unknown>;
  questions: Array<Record<string, any>>;
  created_at: string;
  course_publication?: {
    id: string;
    course_id: string;
    quiz_id: string;
    title: string;
    status: string;
    due_at: string | null;
    available_from: string | null;
    answer_visible_at: string | null;
    attempt_limit: number | null;
    published_at: string;
    created_by: string;
  };
  latest_attempt?: {
    id: string;
    quiz_id: string;
    total_score: number | null;
    duration_sec: number | null;
    completed_at: string;
  } | null;
}

export interface QuizDiagnostic {
  question_index: number;
  question: string | null;
  submitted_answer: unknown;
  answer: unknown;
  is_correct: boolean;
  explanation?: string | null;
  source_page?: number | null;
}

export interface CourseProgressStudent {
  user_id: string;
  username: string;
  email: string | null;
  role: string;
  chat_sessions: number;
  chat_messages: number;
  notes: number;
  flashcards: number;
  flashcards_due: number;
  flashcards_mastered: number;
  quizzes: number;
  assigned_quizzes: number;
  quiz_attempts: number;
  quiz_avg_score: number;
  last_activity_at: string | null;
  risk_level: "ok" | "medium" | "high" | string;
}

export interface CourseQuizSummary {
  course_quiz_id: string;
  quiz_id: string;
  course_id: string;
  title: string;
  due_at: string | null;
  published_at: string;
  student_count: number;
  submission_count: number;
  attempt_count: number;
  score_avg: number;
  weak_items: Array<Record<string, any>>;
  items: Array<Record<string, any>>;
}

export interface CourseQuestionBankItem {
  id: string;
  course_id: string;
  course_quiz_id: string;
  quiz_id: string;
  quiz_title: string;
  course_quiz_title: string;
  question_index: number;
  question_type: string | null;
  question: Record<string, any>;
  status: "draft" | "approved" | "rejected" | "archived" | string;
  review_note: string | null;
  created_by: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CourseProgress {
  course_id: string;
  document_count: number;
  published_quizzes: number;
  students: CourseProgressStudent[];
  quiz_summary: CourseQuizSummary[];
}

export interface CourseAssignmentItem {
  id: string;
  course_id: string;
  created_by: string;
  title: string;
  description: string | null;
  kind: "custom" | "quiz" | "read_summary" | "note" | "flashcards" | string;
  doc_id: string | null;
  doc_filename: string | null;
  quiz_id: string | null;
  quiz_title: string | null;
  due_at: string | null;
  status: "published" | "draft" | "archived" | string;
  created_at: string;
  completion: {
    status: "pending" | "completed" | "late" | "overdue" | string;
    completed_at: string | null;
    source: string | null;
    is_late: boolean;
    score: number | null;
  };
}

export interface CourseAnnouncementItem {
  id: string;
  course_id: string;
  course_title?: string;
  created_by: string;
  created_by_username: string | null;
  title: string;
  content: string;
  status: "published" | "draft" | "archived" | string;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CourseHelpRequestItem {
  id: string;
  course_id: string;
  course_title?: string;
  user_id: string;
  username: string | null;
  session_id: string | null;
  assigned_to: string | null;
  title: string;
  content: string | null;
  status: "open" | "in_progress" | "resolved" | string;
  priority: "low" | "normal" | "high" | string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CourseDashboard {
  announcements: CourseAnnouncementItem[];
  help_requests: CourseHelpRequestItem[];
  managed_help_count: number;
}

export interface NoteItem {
  id: string;
  doc_id: string | null;
  session_id: string | null;
  content: string;
  source_page: number | null;
  source_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalItem {
  id: string;
  doc_id: string;
  title: string;
  target_date: string;
  focus_hint: string | null;
  status: "active" | "completed" | "abandoned";
  created_at: string;
}

export interface CourseItem {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  join_code: string | null;
  role: string;
  is_active: number;
  created_at: string;
  documents?: Array<
    Pick<
      DocumentItem,
      | "id"
      | "filename"
      | "status"
      | "course_status"
      | "page_count"
      | "chunk_count"
      | "created_at"
    >
  >;
}

export interface CostStats {
  today: { total_usd: number; by_feature: Record<string, number> };
  this_month: { total_usd: number; by_feature: Record<string, number> };
  top_users: { user_id: string; username: string; total_usd: number }[];
  daily_series: { date: string; total_usd: number }[];
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (res.status === 401 && path !== "/auth/refresh") {
    const refreshed = await refreshToken();
    if (refreshed) return apiFetch<T>(path, options);
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorMessage(err));
  }
  return res.json() as Promise<T>;
}

export async function apiBlob(
  path: string,
  options: RequestInit = {},
): Promise<Blob> {
  const token = localStorage.getItem("access_token");
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (res.status === 401 && path !== "/auth/refresh") {
    const refreshed = await refreshToken();
    if (refreshed) return apiBlob(path, options);
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorMessage(err));
  }
  return res.blob();
}

export async function refreshToken(): Promise<boolean> {
  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return false;
  const data = (await res.json()) as AuthResponse;
  localStorage.setItem("access_token", data.access_token);
  return true;
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<T>(path, { method: "POST", body: form });
}

export async function apiUploadMany<T>(
  path: string,
  files: File[],
): Promise<T> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  return apiFetch<T>(path, { method: "POST", body: form });
}

function errorMessage(err: any) {
  if (typeof err?.detail === "string") return err.detail;
  if (typeof err?.detail?.message === "string") return err.detail.message;
  if (typeof err?.message === "string") return err.message;
  return "Request failed";
}
