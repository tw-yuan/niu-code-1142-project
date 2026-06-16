import { BASE_URL, Citation } from "./api"

export type StreamEvent =
  | { type: "chunk"; content: string }
  | { type: "citations"; data: Citation[] }
  | { type: "quiz_meta"; data: { quiz_id: string; question_count?: number } }
  | { type: "mindmap_meta"; data: { mindmap_id: string } }
  | { type: "flashcard_meta"; data: { count: number } }
  | { type: "summary_meta"; data: { summary_id: string } }
  | { type: "error"; code: string; message: string }

export async function* streamFetch(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const token = localStorage.getItem("access_token")
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: "include",
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}))
    throw new Error(
      typeof err.detail === "string" ? err.detail : err.detail?.message ?? "Request failed",
    )
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split("\n\n")
    buffer = parts.pop() ?? ""
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue
      const raw = part.slice(6).trim()
      if (raw === "[DONE]") return
      yield JSON.parse(raw) as StreamEvent
    }
  }
}
