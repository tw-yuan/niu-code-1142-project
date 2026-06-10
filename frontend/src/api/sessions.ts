import client from "./client";

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  context_chunks_used?: Array<{ chunk_index: number; source_label?: string; snippet: string; text?: string }> | null;
  quiz_metadata?: {
    kind: "quiz";
    question_count?: number | null;
    score?: number | null;
    status?: "generated" | "graded";
    student_input_preview?: string;
  } | null;
  created_at: string;
}

export interface LearningSession {
  id: number;
  document_id: number;
  direction_key: string;
  direction_label: string;
  direction_emoji: string | null;
  title: string | null;
  message_count: number;
  last_message_preview: string | null;
  quiz_attempts: number;
  quiz_average_score: number | null;
  created_at: string;
  document_original_filename: string | null;
}

export interface SessionDetail extends LearningSession {
  messages: Message[];
}

export async function createSession(payload: {
  document_id: number;
  direction_key: string;
  direction_label: string;
  direction_description?: string;
  direction_emoji?: string;
}): Promise<LearningSession> {
  const { data } = await client.post("/sessions", payload);
  return data;
}

export async function listSessions(): Promise<LearningSession[]> {
  const { data } = await client.get("/sessions");
  return data;
}

export async function getSession(id: number): Promise<SessionDetail> {
  const { data } = await client.get(`/sessions/${id}`);
  return data;
}

export async function deleteSession(id: number): Promise<void> {
  await client.delete(`/sessions/${id}`);
}

export async function updateSession(id: number, payload: { title?: string | null }): Promise<LearningSession> {
  const { data } = await client.patch(`/sessions/${id}`, payload);
  return data;
}
