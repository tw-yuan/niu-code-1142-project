import client from "./client";

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  context_chunks_used?: Array<{ chunk_index: number; snippet: string; text?: string }> | null;
  created_at: string;
}

export interface LearningSession {
  id: number;
  document_id: number;
  direction_key: string;
  direction_label: string;
  direction_emoji: string | null;
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
